"""
NL2Cypher Agent — 基于 ReActAgent 的知识图谱构建 Agent

从自然语言中抽取实体和关系，智能验证并插入 Neo4j 数据库。
支持多步推理、工具调用、结果追溯。
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from Base.Ai.base.baseAgent import ReActAgent
from Base.Ai.base.baseTool import BaseTool
from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Client.neo4jClient import Neo4jClient
from Base.Models.graphModel import Entity, Relation
from Base.Service.neo4jService import parse_nl_2_graph

logger = logging.getLogger(__name__)


# ────────────────────────── 工具定义 ──────────────────────────

class ExtractGraphArgs(BaseModel):
    text: str = Field(..., description="要抽取的自然语言文本")
    schema: Optional[dict] = Field(None, description="可选的 schema 约束")


class ExtractGraphTool(BaseTool):
    """调用轻量解析函数，获取实体和关系列表"""

    name = "ExtractGraphTool"
    description = "从自然语言文本中抽取实体和关系，返回 JSON 格式的实体和关系列表"
    args_schema = ExtractGraphArgs

    def execute(self, text: str, schema: Optional[dict] = None) -> str:
        entities, relations = parse_nl_2_graph(text, schema=schema)
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


class CheckNodeArgs(BaseModel):
    label: str = Field(..., description="实体类型标签，如 'Person'")
    properties: dict = Field(..., description="用于匹配实体的属性字典")


class CheckNodeTool(BaseTool):
    """查询 Neo4j 中节点是否已存在"""

    name = "CheckNodeTool"
    description = "检查 Neo4j 数据库中是否存在指定节点"
    args_schema = CheckNodeArgs

    def __init__(self, client: Neo4jClient):
        super().__init__()
        self.client = client

    def execute(self, label: str, properties: dict) -> str:
        result = self.client.get_node(label, properties)
        if result:
            return json.dumps({"exists": True, "node": result[0]}, ensure_ascii=False, indent=2)
        return json.dumps({"exists": False}, ensure_ascii=False, indent=2)


class InsertNodeArgs(BaseModel):
    label: str = Field(..., description="实体类型标签，如 'Person'")
    properties: dict = Field(..., description="实体属性字典")


class InsertNodeTool(BaseTool):
    """插入新节点"""

    name = "InsertNodeTool"
    description = "在 neo4j 数据库中创建新节点"
    args_schema = InsertNodeArgs

    def __init__(self, client: Neo4jClient):
        super().__init__()
        self.client = client

    def execute(self, label: str, properties: dict) -> str:
        result = self.client.create_node(label, properties)
        if result:
            return json.dumps({"success": True, "node": result[0]}, ensure_ascii=False, indent=2)
        return json.dumps({"success": False, "error": "创建节点返回空结果"}, ensure_ascii=False, indent=2)


class InsertRelationArgs(BaseModel):
    from_label: str = Field(..., description="起始节点类型标签")
    from_props: dict = Field(..., description="起始节点属性")
    to_label: str = Field(..., description="目标节点类型标签")
    to_props: dict = Field(..., description="目标节点属性")
    rel_type: str = Field(..., description="关系类型，如 'FOUNDED'")
    rel_props: dict = Field(default_factory=dict, description="关系属性（可选）")


class InsertRelationTool(BaseTool):
    """插入新关系"""

    name = "InsertRelationTool"
    description = "在 neo4j 数据库中两个节点之间创建关系"
    args_schema = InsertRelationArgs

    def __init__(self, client: Neo4jClient):
        super().__init__()
        self.client = client

    def execute(self, from_label: str, from_props: dict, to_label: str, to_props: dict,
                rel_type: str, rel_props: Optional[dict] = None) -> str:
        result = self.client.create_relationship(
            from_label=from_label,
            from_props=from_props,
            to_label=to_label,
            to_props=to_props,
            rel_type=rel_type,
            rel_props=rel_props or {},
        )
        if result:
            return json.dumps({"success": True, "relationship": result[0]}, ensure_ascii=False, indent=2)
        return json.dumps({"success": False, "error": "创建关系返回空结果，可能节点不存在"}, ensure_ascii=False, indent=2)


# ────────────────────────── Agent 定义 ──────────────────────────

NL2CYPHER_SYSTEM_PROMPT = (
    "你是一个知识图谱构建 Agent。你的任务是从用户输入的文本中抽取实体和关系，并插入 Neo4j 数据库。\n\n"
    "工作流程：\n"
    "1. 使用 ExtractGraphTool 从文本中抽取实体和关系\n"
    "2. 对每个实体，使用 CheckNodeTool 检查是否已存在\n"
    "3. 对不存在的实体，使用 InsertNodeTool 插入\n"
    "4. 所有实体插入完成后，使用 InsertRelationTool 插入关系\n"
    "5. 完成后告知用户结果（成功创建了多少实体和关系）\n\n"
    "注意：\n"
    "- 插入关系前确保两端节点都已存在\n"
    "- 如果某个节点已存在，跳过插入\n"
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
        max_iterations: int = 10,
        **kwargs: Any,
    ):
        llm = get_default_qwen_llm()

        tools = [
            ExtractGraphTool(),
            CheckNodeTool(client),
            InsertNodeTool(client),
            InsertRelationTool(client),
        ]

        super().__init__(
            llm=llm,
            name=name,
            system_prompt=system_prompt or NL2CYPHER_SYSTEM_PROMPT,
            tools=tools,
            max_iterations=max_iterations,
            **kwargs,
        )

        self._client = client

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
                "output": result.output,
                "success": result.success,
                "tool_calls": len(result.tool_calls),
            }, ensure_ascii=False)
            call_log.output_data = output_data
            call_log.status = "success" if result.success else "failed"
            if result.error_msg:
                call_log.error_msg = result.error_msg
            call_log.duration_ms = result.duration_ms
            call_log.iterations = result.iterations
            call_log.save()

            return result

        except Exception as e:
            call_log.status = "failed"
            call_log.error_msg = str(e)
            call_log.duration_ms = int((time.time() - start_time) * 1000)
            call_log.save()
            raise
