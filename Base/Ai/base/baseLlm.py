from abc import abstractmethod, ABC
from typing import Any, Dict, List, Generator, AsyncGenerator, Optional, Union

from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.base.baseSetting import LLMConfig


class BaseLlm(ABC):
    """
    LLM 抽象基类

    定义所有 LLM 实现必须遵循的接口。
    """

    def __init__(
        self,
        model_name: str,
        model_type: Optional[LLMTypeEnum] = None,
        config: Optional[LLMConfig] = None,
        **default_params: Any
    ):
        """
        初始化 LLM 基类

        Args:
            model_name: 模型名称
            model_type: 模型类型枚举
            config: LLM 配置对象
            **default_params: 默认参数
        """
        self.model_name = model_name
        self.model_type: Optional[LLMTypeEnum] = model_type
        self.config = config
        self.model_client = None

        # 合并配置参数和默认参数
        if config:
            config_dict = config.to_dict()
            default_params = {**config_dict, **default_params}

        self.default_params = default_params

    @abstractmethod
    def init_model(self):
        pass

    @abstractmethod
    def invoke(self, prompt: str, **kwargs: Any) -> str:
        pass

    @abstractmethod
    async def ainvoke(self, prompt: str, **kwargs: Any) -> str:
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Union[Dict[str, str], Any]],
        **kwargs: Any
    ) -> str:
        """对话模式同步调用"""
        pass

    @abstractmethod
    async def achat(
        self,
        messages: List[Union[Dict[str, str], Any]],
        **kwargs: Any
    ) -> str:
        """对话模式异步调用"""
        pass

    @abstractmethod
    def stream(self, prompt: str, **kwargs: Any) -> Generator[str, None, None]:
        pass

    @abstractmethod
    async def astream(
            self, prompt: str, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        pass

    @property
    @abstractmethod
    def context_window(self) -> int:
        """获取模型的上下文窗口大小"""
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            包含模型信息的字典，包含模型名称、类型、上下文窗口等
        """
        return {
            "model_name": self.model_name,
            "model_type": self.model_type.value if self.model_type else None,
            "context_window": self.context_window,
            "supports_streaming": self.supports_streaming,
        }
