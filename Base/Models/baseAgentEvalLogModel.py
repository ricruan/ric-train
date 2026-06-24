"""Agent 评估记录模型"""
from datetime import datetime
from typing import Optional, ClassVar

from pydantic import Field

from Base.Repository.models.moduleDbModel import BaseModuleDBModel


class BaseAgentEvalLog(BaseModuleDBModel):
    """Agent 评估记录模型"""
    table_alias: ClassVar[str] = "base_agent_eval_log"
    create_table_sql: ClassVar[str] = f"""
        CREATE TABLE `{table_alias}` (
            `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
            `agent_call_id` BIGINT UNSIGNED COMMENT 'FK → base_agent_call_log.id',
            `evaluator_name` VARCHAR(100) COMMENT '评估器名称',
            `score` DECIMAL(5,4) COMMENT '总分（0-1）',
            `dimensions` JSON COMMENT '多维度评分',
            `feedback` TEXT COMMENT '评估反馈',
            `metadata` JSON COMMENT '额外元数据',
            `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            PRIMARY KEY (`id`),
            KEY `idx_agent_call_id` (`agent_call_id`),
            KEY `idx_evaluator_name` (`evaluator_name`),
            KEY `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='Agent 评估记录表';
    """

    id: Optional[int] = Field(None, description="主键ID")
    agent_call_id: Optional[int] = Field(None, description="FK → base_agent_call_log.id")
    evaluator_name: Optional[str] = Field(None, description="评估器名称")
    score: Optional[float] = Field(None, description="总分（0-1）")
    dimensions: Optional[str] = Field(None, description="多维度评分 JSON")
    feedback: Optional[str] = Field(None, description="评估反馈")
    metadata: Optional[str] = Field(None, description="额外元数据 JSON")
    created_at: Optional[datetime] = Field(None, description="创建时间")
