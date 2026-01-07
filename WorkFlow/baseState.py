from pydantic import BaseModel, Field


class BaseState(BaseModel):
    # id: str = Field(None, description='唯一标识')
    name: str = Field(None, description='节点名称')

    @staticmethod
    def find_me(*args, **kwargs):
        for arg in args:
            if isinstance(arg, BaseState):
                return arg

        for arg in kwargs.values():
            if isinstance(arg, BaseState):
                return arg
        return None
    pass
