"""
NL2Cypher Agent — 基于 ReActAgent 的知识图谱构建 Agent

从自然语言中抽取实体和关系，智能验证并插入 Neo4j 数据库。
支持多步推理、工具调用、结果追溯。
"""
import json
import logging
import time
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from Base.Ai.base.baseAgent import ReActAgent
from Base.Ai.base.baseTool import BaseTool
from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Client.neo4jClient import Neo4jClient
from Base.Service.neo4jService import parse_nl_2_graph

logger = logging.getLogger(__name__)


# ────────────────────────── 工具定义 ──────────────────────────

class ExtractGraphArgs(BaseModel):
    text: str = Field(..., description="要抽取的自然语言文本")
    graph_schema: Optional[dict] = Field(None, description="可选的 schema 约束")


class ExtractGraphTool(BaseTool):
    """调用轻量解析函数，获取实体和关系列表"""

    name = "ExtractGraphTool"
    description = "从自然语言文本中抽取实体和关系，返回 JSON 格式的实体和关系列表"
    args_schema = ExtractGraphArgs

    def execute(self, text: str, graph_schema: Optional[dict] = None) -> str:
        entities, relations = parse_nl_2_graph(text, schema=graph_schema)
        result = {
            "entities": [
                {"label": e.label, "properties": e.properties}
                for e in entities
            ],
            "relations": [
                {
                    "rel_type": r.rel_type,
                    "from_entity": {"label": r.from_entity.label, "properties": r.from_entity.properties},
                    "to_entity": {"label": r.to_entity.label, "properties": r.to_entity.properties},
                    "properties": r.properties,
                }
                for r in relations
            ],
            "entity_count": len(entities),
            "relation_count": len(relations),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)


class InsertGraphArgs(BaseModel):
    entities: list = Field(..., description="实体列表，每项包含 label 和 properties")
    relations: list = Field(default_factory=list, description="关系列表，每项包含 from_entity, to_entity, rel_type")


class InsertGraphTool(BaseTool):
    """批量插入实体和关系到 Neo4j（一次调用完成）"""

    name = "InsertGraphTool"
    description = "批量创建实体并建立关系，一次调用完成所有插入"
    args_schema = InsertGraphArgs

    def __init__(self, client: Neo4jClient):
        super().__init__()
        self.client = client

    def execute(self, entities: list, relations: Optional[list] = None) -> str:
        if relations is None:
            relations = []

        inserted = 0
        skipped = 0
        rels_created = 0
        rels_failed = 0

        for e in entities:
            try:
                result = self.client.create_node(e["label"], e.get("properties", {}))
                if result:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as err:
                logger.error(f"插入实体失败: {e}: {err}")
                skipped += 1

        for r in relations:
            try:
                result = self.client.create_relationship(
                    from_label=r["from_entity"]["label"],
                    from_props=r["from_entity"].get("properties", {}),
                    to_label=r["to_entity"]["label"],
                    to_props=r["to_entity"].get("properties", {}),
                    rel_type=r["rel_type"],
                    rel_props=r.get("properties", {}),
                )
                if result:
                    rels_created += 1
                else:
                    rels_failed += 1
            except Exception as err:
                logger.error(f"插入关系失败: {r}: {err}")
                rels_failed += 1

        return json.dumps({
            "entities_inserted": inserted,
            "entities_skipped": skipped,
            "relations_created": rels_created,
            "relations_failed": rels_failed,
        }, ensure_ascii=False, indent=2)


# ────────────────────────── Agent 定义 ──────────────────────────

NL2CYPHER_SYSTEM_PROMPT = (
    "你是一个知识图谱构建 Agent。你的任务是从用户输入的文本中抽取实体和关系，并插入 Neo4j 数据库。\n\n"
    "工作流程：\n"
    "1. 使用 ExtractGraphTool 从文本中抽取实体和关系\n"
    "2. 使用 InsertGraphTool 批量插入所有实体和关系\n"
    "3. 完成后告知用户结果\n\n"
    "注意：InsertGraphTool 会一次性完成所有插入，无需逐个节点或关系单独调用。\n"
    "遇到错误时记录并继续，不要中断流程。\n"
)


class NL2CypherAgent(ReActAgent):
    """
    NL2Cypher Agent — 智能知识图谱构建 Agent

    基于 ReActAgent 范式，通过多步推理和工具调用完成实体/关系抽取与插入。
    """

    def __init__(
        self,
        client: Neo4jClient,
        name: str = "NL2CypherAgent",
        system_prompt: Optional[str] = None,
        max_iterations: int = 5,
        **kwargs: Any,
    ):
        llm = get_default_qwen_llm()

        tools = [
            ExtractGraphTool(),
            InsertGraphTool(client),
        ]

        super().__init__(
            llm=llm,
            name=name,
            system_prompt=system_prompt or NL2CYPHER_SYSTEM_PROMPT,
            tools=tools,
            max_iterations=max_iterations,
            **kwargs,
        )

    def run(self, user_input: str, user_id: Optional[str] = None, session_id: Optional[str] = None, **kwargs: Any) -> "AgentResult":
        """
        覆盖基类 run，增加调用日志记录。

        Args:
            user_input: 用户输入文本
            user_id: 用户 ID（可选）
            session_id: 会话 ID（可选）
            **kwargs: 额外参数
        """
        from Base.Ai.base.baseAgent import AgentResult
        from Base.Models.baseAgentCallLogModel import BaseAgentCallLog

        start_time = time.time()

        # 创建调用记录
        input_data = json.dumps({"text": user_input, "schema": kwargs.get("schema")}, ensure_ascii=False)
        call_log = BaseAgentCallLog(
            agent_name=self.name,
            user_id=user_id,
            session_id=session_id,
            input_data=input_data,
            ai_model=self.llm.model_name,
        )
        call_log.save()

        try:
            result = super().run(user_input, **kwargs)
            output_data = json.dumps({
                "output": result.output[:500] if result.output else "",
                "success": result.success,
            }, ensure_ascii=False)
            call_log.output_data = output_data
            call_log.status = "success" if result.success else "failed"
            if result.error_msg:
                call_log.error_msg = result.error_msg
            call_log.duration_ms = result.duration_ms
            call_log.save()

            return result

        except Exception as e:
            call_log.status = "failed"
            call_log.error_msg = str(e)
            call_log.duration_ms = int((time.time() - start_time) * 1000)
            call_log.save()
            raise


if __name__ == "__main__":
    """集成测试：Agent 模式"""
    from Base.Config.logConfig import setup_logging
    setup_logging()

    client = Neo4jClient()
    agent = NL2CypherAgent(client=client)

    print("=== Agent 模式 ===")
    result = agent.run("马云创立了阿里巴巴，总部在杭州", user_id="test_user", session_id="test_session")
    print(f"成功: {result.success}")
    print(f"输出: {result.output[:200] if result.output else '(空)'}")
    print(f"耗时: {result.duration_ms}ms")

    client.close()