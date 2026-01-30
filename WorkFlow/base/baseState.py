import copy
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict

from Base import default_qwen_llm
from Base.Ai.base.baseLlm import BaseLlm


class BaseState(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=False,  # 👈 关键修改
        extra="forbid"  # 可选：更严格
    )

    ric_id: str = Field(None, description='唯一标识')
    name: str = Field('', description='工作流名称')
    early_stop_flag: bool = Field(False, description='是否提前停止')




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

    # def __deepcopy__(self, memo: dict[int, Any] | None = None):
    #     """自定义深拷贝，排除 default_model 字段"""
    #     cls = self.__class__
    #     m = cls.__new__(cls)
    #     memo[id(self)] = m
    #
    #     # 深拷贝 __dict__，但排除 default_model
    #     _dict = {}
    #     for k, v in self.__dict__.items():
    #         if k == 'default_model':
    #             _dict[k] = v  # 浅拷贝，不递归深拷贝
    #         else:
    #             _dict[k] = copy.deepcopy(v, memo)
    #
    #     # 使用 object.__setattr__ 绕过 Pydantic 的 __setattr__
    #     object.__setattr__(m, '__dict__', _dict)
    #     object.__setattr__(m, '__pydantic_fields_set__', copy.copy(self.__pydantic_fields_set__))
    #     object.__setattr__(m, '__pydantic_extra__', copy.deepcopy(self.__pydantic_extra__, memo=memo))
    #
    #     if not hasattr(self, '__pydantic_private__') or self.__pydantic_private__ is None:
    #         object.__setattr__(m, '__pydantic_private__', None)
    #     else:
    #         object.__setattr__(
    #             m,
    #             '__pydantic_private__',
    #             copy.deepcopy({k: v for k, v in self.__pydantic_private__.items()}, memo=memo),
    #         )
    #
    #     return m
