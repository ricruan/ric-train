from pydantic import BaseModel, Field


class BaseState(BaseModel):
    # id: str = Field(None, description='唯一标识')
    name: str = Field(None, description='节点名称')
    pass
