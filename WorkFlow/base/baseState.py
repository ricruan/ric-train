from typing import Any, Optional

from pydantic import BaseModel, Field


class BaseState(BaseModel):
    # id: str = Field(None, description='唯一标识')
    name: str = Field('', description='工作流名称')
    early_stop_flag: bool = Field(False, description='是否提前停止')

    def __init__(self, /, **data: Any):
        super().__init__(**data)

    @staticmethod
    def find_me(*args, **kwargs) -> Optional[BaseModel]:
        """
        从不定参数中找到我
        :param args:
        :param kwargs:
        :return:
        """
        for arg in args:
            if isinstance(arg, BaseState):
                return arg

        for arg in kwargs.values():
            if isinstance(arg, BaseState):
                return arg
        return None
