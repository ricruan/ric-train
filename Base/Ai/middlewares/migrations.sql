-- =====================================================
-- Agent 中间件系统数据库迁移脚本
-- =====================================================

-- 1. 修改 base_agent_call_log 表，添加 token 统计字段
ALTER TABLE `base_agent_call_log`
ADD COLUMN `prompt_tokens` INT UNSIGNED DEFAULT 0 COMMENT 'Prompt tokens 消耗' AFTER `ai_model`,
ADD COLUMN `completion_tokens` INT UNSIGNED DEFAULT 0 COMMENT 'Completion tokens 消耗' AFTER `prompt_tokens`,
ADD COLUMN `total_tokens` INT UNSIGNED DEFAULT 0 COMMENT '总 tokens 消耗' AFTER `completion_tokens`;

-- 2. 修改 base_agent_tool_call_log 表，添加创建时间字段
ALTER TABLE `base_agent_tool_call_log`
ADD COLUMN `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间' AFTER `call_order`,
ADD INDEX `idx_created_at` (`created_at`);

-- 3. 创建 base_agent_eval_log 表
CREATE TABLE `base_agent_eval_log` (
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
