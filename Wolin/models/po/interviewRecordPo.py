import json
from datetime import datetime
from typing import Optional, ClassVar

from pydantic import Field

from Wolin.db.connectionInit import WolinModuleDBModel


class InterviewRecordPo(WolinModuleDBModel):
    """
    面试分析记录表实体类
    """
    table_alias: ClassVar[str] = 'interview_records'
    create_table_sql = f"""
        -- 面试分析记录表
        CREATE TABLE IF NOT EXISTS `{table_alias}` (
            -- 核心 ID
            `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '面试记录 ID',
            `record_uuid` VARCHAR(36) NOT NULL DEFAULT (UUID()) COMMENT '面试记录 UUID',

            -- 用户信息
            `user_name` VARCHAR(100) NOT NULL COMMENT '用户姓名',
            `user_email` VARCHAR(255) COMMENT '用户邮箱',
            `company_name` VARCHAR(200) COMMENT '面试公司名称',

            -- 文件资源
            `audio_file_path` VARCHAR(500) COMMENT '原始音频文件路径',
            `audio_duration` INT UNSIGNED COMMENT '音频时长（秒）',
            `audio_text_path` VARCHAR(500) COMMENT 'ASR 转写文本路径',
            `audio_text_origin_path` VARCHAR(500) COMMENT 'ASR 原始转写文本路径',
            `resume_file_path` VARCHAR(500) COMMENT '简历文件路径',
            `report_file_path` VARCHAR(500) COMMENT '面试报告路径',

            -- ASR 结果（TEXT 存储 JSON 字符串）
            `audio_text` TEXT COMMENT '音频转写全文',
            `qa_pairs` TEXT COMMENT '问答对（JSON 字符串）',

            -- 简历解析（TEXT 存储 JSON 字符串）
            `resume_info` TEXT COMMENT '简历解析信息（JSON 字符串）',

            -- AI 分析报告（TEXT 存储 JSON 字符串或纯文本）
            `analysis_start` TEXT COMMENT '报告开篇语',
            `interview_json` TEXT COMMENT '面试详情表格（JSON 字符串）',
            `qa_analysis` TEXT COMMENT '问答对分析点评（JSON 字符串）',
            `resume_analysis` TEXT COMMENT '简历分析点评',
            `interview_evaluation` TEXT COMMENT 'AI 面试官评价',
            `self_evaluation` TEXT COMMENT 'AI 求职者自我评价',
            `analysis_end` TEXT COMMENT '报告结束语',

            -- 任务状态
            `status` VARCHAR(20) DEFAULT 'processing' COMMENT '状态：processing|completed|failed',
            `error_msg` TEXT COMMENT '错误信息',

            -- 审计字段
            `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            `completed_at` DATETIME COMMENT '完成时间',

            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_record_uuid` (`record_uuid`),
            KEY `idx_user_name` (`user_name`),
            KEY `idx_company_name` (`company_name`),
            KEY `idx_status` (`status`),
            KEY `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试分析记录表';
        """

    # 核心 ID
    id: Optional[int] = Field(None, description="面试记录 ID")
    record_uuid: Optional[str] = Field(None, description="面试记录 UUID")

    # 用户信息
    user_name: str = Field(..., description="用户姓名")
    user_email: Optional[str] = Field(None, description="用户邮箱")
    company_name: Optional[str] = Field(None, description="面试公司名称")

    # 文件资源
    audio_file_path: Optional[str] = Field(None, description="原始音频文件路径")
    audio_duration: Optional[int] = Field(None, description="音频时长（秒）")
    audio_text_path: Optional[str] = Field(None, description="ASR 转写文本路径")
    audio_text_origin_path: Optional[str] = Field(None, description="ASR 原始转写文本路径")
    resume_file_path: Optional[str] = Field(None, description="简历文件路径")
    report_file_path: Optional[str] = Field(None, description="面试报告路径")

    # ASR 结果
    audio_text: Optional[str] = Field(None, description="音频转写全文")
    qa_pairs: Optional[str] = Field(None, description="问答对（JSON 字符串）")

    # 简历解析
    resume_info: Optional[str] = Field(None, description="简历解析信息（JSON 字符串）")

    # AI 分析报告
    analysis_start: Optional[str] = Field(None, description="报告开篇语")
    interview_json: Optional[str] = Field(None, description="面试详情表格（JSON 字符串）")
    qa_analysis: Optional[str] = Field(None, description="问答对分析点评（JSON 字符串）")
    resume_analysis: Optional[str] = Field(None, description="简历分析点评")
    interview_evaluation: Optional[str] = Field(None, description="AI 面试官评价")
    self_evaluation: Optional[str] = Field(None, description="AI 求职者自我评价")
    analysis_end: Optional[str] = Field(None, description="报告结束语")

    # 任务状态
    status: str = Field('processing', description="状态：processing|completed|failed")
    error_msg: Optional[str] = Field(None, description="错误信息")

    # 审计字段
    created_at: Optional[datetime] = Field(None, description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    def set_json_field(self, field_name: str, value):
        """
        设置 JSON 字段，自动序列化为 JSON 字符串

        Args:
            field_name: 字段名（qa_pairs, resume_info, interview_json, qa_analysis）
            value: 要存储的值（dict/list/str）
        """
        if value is None:
            setattr(self, field_name, None)
        elif isinstance(value, (dict, list)):
            setattr(self, field_name, json.dumps(value, ensure_ascii=False))
        else:
            setattr(self, field_name, str(value))

    def get_json_field(self, field_name: str):
        """
        获取 JSON 字段，自动解析为 Python 对象

        Args:
            field_name: 字段名（qa_pairs, resume_info, interview_json, qa_analysis）

        Returns:
            解析后的 Python 对象（dict/list），如果字段为空或解析失败则返回 None
        """
        value = getattr(self, field_name, None)
        if value is None or not value.strip():
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, Exception):
            return None

    @property
    def get_qa_pairs(self) -> Optional[dict | list]:
        """获取问答对（解析后）"""
        return self.get_json_field('qa_pairs')

    @property
    def get_resume_info(self) -> Optional[dict]:
        """获取简历信息（解析后）"""
        return self.get_json_field('resume_info')

    @property
    def get_interview_json(self) -> Optional[dict]:
        """获取面试详情表格（解析后）"""
        return self.get_json_field('interview_json')

    @property
    def get_qa_analysis(self) -> Optional[dict | list]:
        """获取问答分析（解析后）"""
        return self.get_json_field('qa_analysis')

    @classmethod
    def create_from_state(cls, state) -> 'InterviewRecordPo':
        """
        从 IAState 创建记录实例

        Args:
            state: IAState 实例

        Returns:
            InterviewRecordPo 实例
        """
        record = cls(
            user_name=state.api_params.user_name or '',
            user_email=state.api_params.receive_email,
            company_name=state.api_params.company_name,
        )

        # 设置 ASR 信息
        if state.asr_info:
            record.audio_file_path = state.asr_info.audio_path
            record.audio_text = state.asr_info.audio_text
            record.set_json_field('qa_pairs', state.asr_info.qa_pairs)

        # 设置简历信息
        if state.resume_info:
            record.resume_file_path = state.resume_info.resume_path
            record.set_json_field('resume_info', state.resume_info.model_dump(exclude_none=True))

        # 设置报告信息
        if state.report:
            record.analysis_start = state.report.analysis_start
            record.set_json_field('interview_json', state.report.interview_json)
            record.set_json_field('qa_analysis', state.report.qa_analysis)
            record.resume_analysis = state.report.resume_analysis
            record.interview_evaluation = state.report.interview_evaluation
            record.self_evaluation = state.report.self_evaluation
            record.analysis_end = state.report.analysis_end

        return record


if __name__ == '__main__':
    # 测试创建表
    po = InterviewRecordPo()
    po.create_table()
    print("面试分析记录表创建成功")
