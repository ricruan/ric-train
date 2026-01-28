import copy
from typing import Optional, Any

from pydantic import Field, BaseModel

from WorkFlow.base.baseState import BaseState


class Report(BaseModel):
    report_paragraph1: Optional[str] = Field(None, description='报告段落1')


class ASRInfo(BaseModel):
    audio_path: Optional[str] = Field(None, description='音频地址')
    audio_text: Optional[str] = Field(None, description='音频文本')


class ResumeInfo(BaseModel):
    name: Optional[str] = Field(None, description='姓名')
    age: Optional[int] = Field(None, description='年龄')
    sex: Optional[str] = Field(None, description='性别')
    education: Optional[str] = Field(None, description='教育背景')
    graduation_time: Optional[str] = Field(None, description='毕业时间')
    major: Optional[str] = Field(None, description='专业')
    last_company: Optional[str] = Field(None, description='上一份工作公司')
    last_position: Optional[str] = Field(None, description='上一份工作职位')
    last_salary: Optional[str] = Field(None, description='上一份工作薪资')
    last_start_time: Optional[str] = Field(None, description='上一份工作时间')
    last_end_time: Optional[str] = Field(None, description='上一份工作时间')
    last_duration: Optional[str] = Field(None, description='上一份工作周期')
    intent_position: Optional[str] = Field(None, description='期望工作岗位')
    resume_path: Optional[str] = Field(None, description='简历路径')

class IAState(BaseState):
    report: Optional[Report] = Field(None, description='报告')
    asr_info: Optional[ASRInfo] = Field(None, description='asr信息')
    resume_info: Optional[ResumeInfo] = Field(None, description='简历信息')

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        self.resume_info = ResumeInfo()



