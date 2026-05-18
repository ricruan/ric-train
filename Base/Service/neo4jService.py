"""
NL2Cypher 服务：从自然语言抽取实体和关系并插入 Neo4j

支持两种模式：
- 轻量模式：extract_graph / extract_and_insert
- Agent 模式：见 Base/Ai/agents/nl2cypherAgent.py
"""
import json
import logging
import time
from typing import List, Optional, Tuple

from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Client.neo4jClient import Neo4jClient
from Base.Models.graphModel import Entity, Relation, ExtractionResult

logger = logging.getLogger(__name__)


# ────────────────────────── 自定义异常 ──────────────────────────

class LLMExtractionError(Exception):
    """LLM 抽取失败"""
    pass


class ParseError(Exception):
    """JSON 解析失败"""
    pass


class Neo4jConnectionError(Exception):
    """Neo4j 连接异常"""
    pass


# ────────────────────────── 轻量解析函数 ──────────────────────────

def parse_nl_2_graph(
    text: str,
    llm=None,
    schema: Optional[dict] = None,
) -> Tuple[List[Entity], List[Relation]]:
    """
    从自然语言文本中抽取实体和关系。

    Args:
        text: 自然语言文本
        llm: LLM 实例，默认使用 get_default_qwen_llm()
        schema: 可选的 schema 约束，格式 {"entity_types": [...], "rel_types": [...]}

    Returns:
        (entities, relations) 元组

    Raises:
        LLMExtractionError: LLM 调用失败
        ParseError: JSON 解析失败（重试一次后）
    """
    if llm is None:
        llm = get_default_qwen_llm()

    prompt = _build_prompt(text, schema)

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        raise LLMExtractionError(f"LLM 调用失败: {e}") from e

    entities, relations = _parse_llm_response(response, text)
    return entities, relations


def _build_prompt(text: str, schema: Optional[dict] = None) -> str:
    """构建 LLM 提示词"""
    base_prompt = (
        "你是一个知识图谱信息抽取专家。请从以下文本中抽取所有实体和关系。\n\n"
        "以 JSON 格式返回，格式如下：\n"
        "{\n"
        '  "entities": [{"label": "类型", "properties": {"key": "value"}}],\n'
        '  "relations": [{"rel_type": "关系类型", "from_entity": 0, "to_entity": 1, "properties": {}}]\n'
        "}\n\n"
        "relations 中的 from_entity 和 to_entity 是 entities 数组的索引。\n\n"
        f"文本：{text}"
    )

    if schema:
        constraint_parts = []
        if "entity_types" in schema:
            constraint_parts.append(f"仅允许使用以下实体类型：{', '.join(schema['entity_types'])}")
        if "rel_types" in schema:
            constraint_parts.append(f"仅允许使用以下关系类型：{', '.join(schema['rel_types'])}")
        base_prompt += "\n\n" + "\n".join(constraint_parts)

    return base_prompt


def _parse_llm_response(response: str, raw_text: str) -> Tuple[List[Entity], List[Relation]]:
    """
    解析 LLM 返回的 JSON 字符串为 Entity/Relation 列表。

    如果解析失败，重试一次。
    """
    for attempt in range(2):
        try:
            data = json.loads(response)
            entities_raw = data.get("entities", [])
            relations_raw = data.get("relations", [])

            entities = [
                Entity(label=e["label"], properties=e.get("properties", {}))
                for e in entities_raw
            ]

            relations = []
            for r in relations_raw:
                from_idx = r.get("from_entity", 0)
                to_idx = r.get("to_entity", 0)
                if 0 <= from_idx < len(entities) and 0 <= to_idx < len(entities):
                    relations.append(Relation(
                        rel_type=r["rel_type"],
                        from_entity=entities[from_idx],
                        to_entity=entities[to_idx],
                        properties=r.get("properties", {}),
                    ))

            return entities, relations

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            if attempt == 0:
                logger.warning(f"JSON 解析失败，重试一次: {e}")
                continue
            raise ParseError(f"无法解析 LLM 返回的 JSON: {response[:500]}") from e

    # 理论上不会到这里
    raise ParseError("未知解析错误")


# ────────────────────────── Neo4jService 类 ──────────────────────────

class Neo4jService:
    """
    Neo4j 业务逻辑服务

    Args:
        client: Neo4jClient 实例，默认自动创建
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        self.client = client or Neo4jClient()

    def extract_graph(
        self,
        text: str,
        schema: Optional[dict] = None,
    ) -> Tuple[List[Entity], List[Relation]]:
        """
        从自然语言中抽取实体和关系（不插入数据库）。

        Args:
            text: 自然语言文本
            schema: 可选的 schema 约束

        Returns:
            (entities, relations) 元组
        """
        return parse_nl_2_graph(text, schema=schema)

    def extract_and_insert(
        self,
        text: str,
        schema: Optional[dict] = None,
    ) -> ExtractionResult:
        """
        从自然语言中抽取实体和关系，并插入 Neo4j 数据库。

        Args:
            text: 自然语言文本
            schema: 可选的 schema 约束

        Returns:
            ExtractionResult 包含创建/跳过的统计信息
        """
        result = ExtractionResult()
        try:
            entities, relations = self.extract_graph(text, schema)
        except (LLMExtractionError, ParseError) as e:
            result.error = str(e)
            return result

        # 去重：用 (label, json.dumps(properties, sort_keys=True)) 作为唯一键
        # 注意：此去重仅在单次调用内生效。跨调用去重需使用 Agent 模式（CheckNodeTool）
        seen_entities = set()

        for entity in entities:
            key = (entity.label, json.dumps(entity.properties, sort_keys=True, ensure_ascii=False))
            if key in seen_entities:
                result.entities_skipped.append(f"重复实体: {entity.label} {entity.properties}")
                continue
            seen_entities.add(key)

            try:
                created = self.client.create_node(entity.label, entity.properties)
                if created:
                    result.entities_created += 1
                else:
                    result.entities_skipped.append(f"插入失败: {entity.label} {entity.properties}")
            except Exception as e:
                logger.error(f"插入实体失败: {e}")
                result.entities_skipped.append(f"{entity.label} {entity.properties}: {e}")

        # 插入关系
        seen_relations = set()
        for rel in relations:
            from_key = (rel.from_entity.label, json.dumps(rel.from_entity.properties, sort_keys=True, ensure_ascii=False))
            to_key = (rel.to_entity.label, json.dumps(rel.to_entity.properties, sort_keys=True, ensure_ascii=False))

            rel_signature = (from_key, rel.rel_type, to_key)
            if rel_signature in seen_relations:
                result.relations_skipped.append(f"重复关系: {rel.rel_type}")
                continue
            seen_relations.add(rel_signature)

            try:
                created = self.client.create_relationship(
                    from_label=rel.from_entity.label,
                    from_props=rel.from_entity.properties,
                    to_label=rel.to_entity.label,
                    to_props=rel.to_entity.properties,
                    rel_type=rel.rel_type,
                    rel_props=rel.properties,
                )
                if created:
                    result.relations_created += 1
                else:
                    result.relations_skipped.append(f"插入失败: {rel.rel_type}")
            except Exception as e:
                logger.error(f"插入关系失败: {e}")
                result.relations_skipped.append(f"{rel.rel_type}: {e}")

        return result


if __name__ == "__main__":
    """集成测试：真实 Neo4j + LLM 端到端"""
    from Base.Config.logConfig import setup_logging
    setup_logging()

    svc = Neo4jService()

    print("=== 轻量模式：抽取 ===")
    entities, relations = svc.extract_graph("马云创立了阿里巴巴，总部在杭州")
    print(f"实体: {len(entities)} 条")
    for e in entities:
        print(f"  {e.label}: {e.properties}")
    print(f"关系: {len(relations)} 条")
    for r in relations:
        print(f"  {r.from_entity.properties.get('name', '?')} -[{r.rel_type}]-> {r.to_entity.properties.get('name', '?')}")

    print("\n=== 轻量模式：抽取 + 插入 ===")
    result = svc.extract_and_insert("马斯克创立了 SpaceX 和 Tesla")
    print(f"实体创建: {result.entities_created}")
    print(f"关系创建: {result.relations_created}")
    if result.entities_skipped:
        print(f"跳过实体: {result.entities_skipped}")
    if result.relations_skipped:
        print(f"跳过关系: {result.relations_skipped}")
    if result.error:
        print(f"错误: {result.error}")