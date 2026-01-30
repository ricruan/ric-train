from typing import Optional, Any, Dict, Annotated

from pydantic import Field, BaseModel

from WorkFlow.base.baseState import BaseState


class Report(BaseModel):
    analysis_start: Optional[str] = Field(None, description='报告段落-开始')
    interview_json: Optional[dict] = Field(None, description='面试详情表格json')
    qa_analysis: Optional[list | str] = Field(None, description='问答对分析点评')
    resume_analysis: Optional[str] = Field(None, description='简历分析点评')
    interview_evaluation: Optional[str] = Field(None, description='AI代入面试评价')
    self_evaluation: Optional[str] = Field(None, description='自我评价')
    analysis_end: Optional[str] = Field(None, description='报告段落-结束')


class ASRInfo(BaseModel):
    audio_path: Optional[str] = Field(None, description='音频路径')
    audio_text: Optional[str] = Field(None, description='音频文本')
    qa_pairs: Optional[list | str] = Field(None, description='问答对')

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

class ApiParams(BaseModel):
    receive_email: Optional[str] = Field(None, description='接收邮箱')
    user_name: Optional[str] = Field(None, description='用户名')
    company_name: Optional[str] = Field(None, description='公司名')


def merge_report(left: Optional[Report], right: Optional[Any]) -> Optional[Report]:
    if right is None:
        return left
    if left is None:
        return Report(**right) if isinstance(right, dict) else right

    # 统一转换为字典
    if isinstance(right, dict):
        right_dict = right
    else:
        right_dict = right.model_dump(exclude_unset=True, exclude_none=True)

    return left.model_copy(update=right_dict)


class IAState(BaseState):
    report: Annotated[Report, merge_report] = Field(default_factory=Report, description='报告')
    asr_info: ASRInfo = Field(default_factory=ASRInfo, description='asr信息')
    resume_info: ResumeInfo = Field(default_factory=ResumeInfo, description='简历信息')
    api_params: ApiParams = Field(default_factory=ApiParams, description='api参数')


    @property
    def context_params(self):
        self.resume_info.name = self.api_params.user_name or self.resume_info.name
        return {
            "resume_info": self.resume_info.model_dump(),
            **(self.report.interview_json or {}),
            **self.report.model_dump(exclude={"interview_json"})
        }

    @property
    def minio_path(self):
        return f'{self.api_params.user_name}/{self.api_params.company_name}.docx'


