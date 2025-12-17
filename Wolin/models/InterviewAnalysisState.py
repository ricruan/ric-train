from pydantic import BaseModel,Field


class InterviewAnalysisState(BaseModel):
    company_name: str = Field(None,description="公司名称")
