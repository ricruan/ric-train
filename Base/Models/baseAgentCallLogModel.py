from datetime import datetime
from typing import Optional, ClassVar, List

from pydantic import Field

from Base.Repository.models.moduleDbModel import BaseModuleDBModel


class BaseAgentCallLog(BaseModuleDBModel):
    """
    Agent 调用主记录模型
    """
    table_alias: ClassVar[str] = "base_agent_call_log"
    create_table_sql: ClassVar[str] = f"""
        CREATE TABLE `{table_alias}` (
            `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
            `agent_name` VARCHAR(100) COMMENT 'Agent 名称',
            `user_id` VARCHAR(64) COMMENT '用户ID',
            `session_id` VARCHAR(64) COMMENT '会话ID',
            `input_data` JSON COMMENT '入参（JSON 格式）',
            `output_data` TEXT COMMENT '出参（最终结果摘要）',
            `status` VARCHAR(20) DEFAULT 'success' COMMENT '状态：success|failed|timeout',
            `error_msg` TEXT COMMENT '错误信息',
            `duration_ms` INT UNSIGNED COMMENT '总耗时（毫秒）',
            `iterations` INT UNSIGNED COMMENT '工具调用循环次数',
            `ai_model` VARCHAR(100) COMMENT '使用的 LLM 模型名称',
            `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            PRIMARY KEY (`id`),
            KEY `idx_agent_name` (`agent_name`),
            KEY `idx_user_id` (`user_id`),
            KEY `idx_session_id` (`session_id`),
            KEY `idx_created_at` (`created_at`),
            KEY `idx_status` (`status`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent 调用记录表';
    """

    id: Optional[int] = Field(None, description="主键ID")
    agent_name: Optional[str] = Field(None, description="Agent 名称")
    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    input_data: Optional[str] = Field(None, description="入参（JSON 格式）")
    output_data: Optional[str] = Field(None, description="出参（最终结果摘要）")
    status: str = Field("success", description="状态：success|failed|timeout")
    error_msg: Optional[str] = Field(None, description="错误信息")
    duration_ms: Optional[int] = Field(None, description="总耗时（毫秒）")
    iterations: Optional[int] = Field(None, description="工具调用循环次数")
    ai_model: Optional[str] = Field(None, description="使用的 LLM 模型名称")
    created_at: Optional[datetime] = Field(None, description="创建时间")

    def get_tool_calls(self) -> List["BaseAgentToolCallLog"]:
        """获取本次调用的所有工具调用明细"""
        from Base.Models.baseAgentToolCallLogModel import BaseAgentToolCallLog
        if self.id is None:
            return []
        return BaseAgentToolCallLog.find_by(agent_call_id=self.id, order_by="call_order", order="ASC")
