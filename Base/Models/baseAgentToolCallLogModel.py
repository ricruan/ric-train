from typing import Optional, ClassVar

from pydantic import Field

from Base.Repository.models.moduleDbModel import BaseModuleDBModel


class BaseAgentToolCallLog(BaseModuleDBModel):
    """
    Agent 工具调用明细模型
    """
    table_alias: ClassVar[str] = "base_agent_tool_call_log"
    create_table_sql: ClassVar[str] = f"""
        CREATE TABLE `{table_alias}` (
            `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
            `agent_call_id` BIGINT UNSIGNED COMMENT 'FK → base_agent_call_log.id',
            `tool_name` VARCHAR(100) COMMENT '工具名称',
            `tool_input` JSON COMMENT '工具入参（JSON 格式）',
            `tool_output` TEXT COMMENT '工具出参',
            `status` VARCHAR(20) DEFAULT 'success' COMMENT '状态：success|failed',
            `error_msg` TEXT COMMENT '工具级错误信息',
            `duration_ms` INT UNSIGNED COMMENT '工具耗时（毫秒）',
            `call_order` INT UNSIGNED COMMENT '调用顺序',
            PRIMARY KEY (`id`),
            KEY `idx_agent_call_id` (`agent_call_id`),
            KEY `idx_tool_name` (`tool_name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent 工具调用明细表';
    """

    id: Optional[int] = Field(None, description="主键ID")
    agent_call_id: Optional[int] = Field(None, description="FK → base_agent_call_log.id")
    tool_name: Optional[str] = Field(None, description="工具名称")
    tool_input: Optional[str] = Field(None, description="工具入参（JSON 格式）")
    tool_output: Optional[str] = Field(None, description="工具出参")
    status: str = Field("success", description="状态：success|failed")
    error_msg: Optional[str] = Field(None, description="工具级错误信息")
    duration_ms: Optional[int] = Field(None, description="工具耗时（毫秒）")
    call_order: Optional[int] = Field(None, description="调用顺序")
