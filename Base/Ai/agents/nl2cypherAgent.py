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

from Base.Ai.base.baseAgent import ReActAgent, AssistantMessages
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
    description = (
        "从自然语言文本中抽取实体和关系，返回 JSON 格式的实体和关系列表。"
        "注意：此工具只做分析，不会修改数据库。抽取完成后必须调用 InsertGraphTool 完成插入。"
    )
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
    description = (
        "批量创建实体并建立关系，一次调用完成所有插入。"
        "接收 ExtractGraphTool 的输出作为输入。"
        "当 ExtractGraphTool 返回实体和关系列表后，必须调用此工具完成数据库写入。"
    )
    args_schema = InsertGraphArgs

    def __init__(self, client: Neo4jClient):
        super().__init__()
        self.client = client

    def execute(self, entities: list, relations: Optional[list] = None) -> str:
        if relations is None:
            relations = []

        logger.info(f"InsertGraphTool 收到: entities={len(entities)}, relations={len(relations)}")

        inserted = 0
        skipped = 0
        rels_created = 0
        rels_failed = 0

        for e in entities:
            logger.info(f"  创建实体: {e['label']} {e.get('properties', {})}")
            result = self.client.create_node(e["label"], e.get("properties", {}))
            logger.info(f"  create_node 返回: {result}")
            if result:
                inserted += 1
            else:
                skipped += 1
                logger.warning(f"  实体插入返回空: {e}")

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
    "你必须严格按以下顺序执行，不可跳过任何步骤：\n"
    "第一步：调用 ExtractGraphTool 从文本中抽取实体和关系\n"
    "第二步：拿到抽取结果后，立即调用 InsertGraphTool 将所有实体和关系批量插入数据库\n"
    "第三步：InsertGraphTool 返回插入结果后，向用户报告最终结果\n\n"
    "重要规则：\n"
    "- ExtractGraphTool 只做分析，不修改数据库。调用完后你必须紧接着调用 InsertGraphTool\n"
    "- InsertGraphTool 会一次性完成所有插入，无需逐个节点或关系单独调用\n"
    "- 不要重复调用 ExtractGraphTool，一次抽取即可\n"
    "- 遇到错误时记录并继续，不要中断流程\n"
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

        # 构建包含工具描述的系统提示词
        base_prompt = system_prompt or NL2CYPHER_SYSTEM_PROMPT
        tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in tools)
        full_prompt = base_prompt + "\n\n你可用的工具：\n" + tools_desc

        super().__init__(
            llm=llm,
            name=name,
            system_prompt=full_prompt,
            tools=tools,
            max_iterations=max_iterations,
            **kwargs,
        )

    def _run_loop(self, messages, **kwargs):
        """
        自定义 ReAct 循环，强制执行两阶段工作流：
        1. 先抽取（由 Agent 控制，不依赖 LLM 选择）
        2. 再让 LLM 决定是否调用 InsertGraphTool
        """
        import time as _time

        messages = list(messages)
        self._tool_call_logs: List[dict] = []

        # 提取用户输入
        user_input = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_input = msg.get("content", "")
                break

        # 阶段 1：直接执行抽取（不经过 LLM 决策），并记录工具调用日志
        extract_tool = self._tools.get("ExtractGraphTool")
        if not extract_tool:
            return super()._run_loop(messages, **kwargs)

        extract_start = _time.time()
        try:
            extract_result = extract_tool.run(text=user_input)
            extract_status = "success"
            extract_error = None
        except Exception as e:
            logger.error(f"抽取失败: {e}")
            extract_result = json.dumps({"entities": [], "relations": [], "error": str(e)}, ensure_ascii=False)
            extract_status = "failed"
            extract_error = str(e)

        self._tool_call_logs.append({
            "tool_name": extract_tool.name,
            "tool_input": json.dumps({"text": user_input}, ensure_ascii=False),
            "tool_output": extract_result[:2000],  # 截断过长输出
            "status": extract_status,
            "error_msg": extract_error,
            "duration_ms": int((_time.time() - extract_start) * 1000),
            "call_order": len(self._tool_call_logs) + 1,
        })

        # 将抽取结果作为用户补充信息追加
        messages.append({
            "role": "user",
            "content": (
                f"[系统] 已从文本中抽取以下知识图谱数据：\n\n{extract_result}\n\n"
                f"请分析这些数据。如果数据有效，请调用 InsertGraphTool 将其插入数据库；"
                f"如果数据为空或无效，请直接说明原因。"
            ),
        })

        # 阶段 2：移除 ExtractGraphTool，只保留 InsertGraphTool
        self.remove_tool("ExtractGraphTool")

        # 阶段 3：让 LLM 决定是否插入
        iteration = 0
        final_text = ""
        insert_called = False
        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Agent [{self.name}] 第 {iteration} 轮循环（插入阶段）")

            response = self._call_llm(messages)
            tc_list = self._extract_tool_calls(response)
            if not tc_list:
                final_text = self._extract_text_content(response)
                break

            for tc in tc_list:
                tool_start = _time.time()
                if tc["name"] == "InsertGraphTool":
                    if insert_called:
                        messages.append({
                            "role": "tool",
                            "content": "数据已插入，无需重复操作。请给出最终结果。",
                            "tool_call_id": tc.get("id", ""),
                        })
                        continue
                    try:
                        tool_result = self._execute_tool_call(tc)
                        insert_status = "success"
                        insert_error = None
                    except Exception as e:
                        tool_result = str(e)
                        insert_status = "failed"
                        insert_error = str(e)

                    self._tool_call_logs.append({
                        "tool_name": "InsertGraphTool",
                        "tool_input": tc.get("arguments", "{}"),
                        "tool_output": str(tool_result)[:2000],
                        "status": insert_status,
                        "error_msg": insert_error,
                        "duration_ms": int((_time.time() - tool_start) * 1000),
                        "call_order": len(self._tool_call_logs) + 1,
                    })
                    messages.append({
                        "role": "tool",
                        "content": str(tool_result),
                        "tool_call_id": tc.get("id", ""),
                    })
                    insert_called = True
                else:
                    messages.append({
                        "role": "tool",
                        "content": "错误: 当前阶段不可用此工具",
                        "tool_call_id": tc.get("id", ""),
                    })

        # 恢复 ExtractGraphTool（以便下次 run 调用）
        self.add_tool(ExtractGraphTool())

        self.memory.add_message(AssistantMessages(prompt=final_text))
        return final_text

    def run(self, user_input: str, user_id: Optional[str] = None, session_id: Optional[str] = None, **kwargs: Any) -> "AgentResult":
        """
        覆盖基类 run，增加调用日志记录（含工具调用明细）。
        """
        from Base.Ai.base.baseAgent import AgentResult
        from Base.Models.baseAgentCallLogModel import BaseAgentCallLog
        from Base.Models.baseAgentToolCallLogModel import BaseAgentToolCallLog

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
            call_log.error_msg = result.error_msg
            call_log.duration_ms = result.duration_ms
            call_log.iterations = result.iterations
            call_log.save()

            # 保存工具调用明细
            if call_log.id and hasattr(self, "_tool_call_logs") and self._tool_call_logs:
                for i, tc in enumerate(self._tool_call_logs, 1):
                    tool_log = BaseAgentToolCallLog(
                        agent_call_id=call_log.id,
                        tool_name=tc["tool_name"],
                        tool_input=tc["tool_input"],
                        tool_output=tc["tool_output"],
                        status=tc["status"],
                        error_msg=tc.get("error_msg"),
                        duration_ms=tc.get("duration_ms", 0),
                        call_order=tc.get("call_order", i),
                    )
                    tool_log.save()

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