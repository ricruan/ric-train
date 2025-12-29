from threading import Event

from pydantic import BaseModel,Field


class InterviewAnalysisState(BaseModel):
    uuid :str = Field(None,description="唯一标识")
    audio_duration: str = Field(None,description="音频时长")
    context_params: dict = Field(None,description="模板上下文字典")
    company_name: str = Field(None,description="公司名称")
    analysis_state_event: Event = Field(None,description="工作流事件")
    content: str = Field(None,description="ASR 文本内容")
    resume_file: str = Field(None,description="简历文件路径，会被处理，可变")
    audio_file: str = Field(None,description="音频文件路径，会被处理，可变")
    origin_resume_file: str = Field(None,description="原始简历文件路径")
    origin_audio_file: str = Field(None,description="原始音频文件路径")
    report_path: str = Field(None,description="报告本地路径")
    user_email : list[str] = Field(None,description="用户收件邮箱")
