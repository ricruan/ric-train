from abc import abstractmethod, ABC
from typing import Any, Dict, List, Generator, AsyncGenerator, Optional

from Base.Ai.base.baseEnum import LLMTypeEnum


class BaseLlm(ABC):
    def __init__(self, model_name: str,model_type : Optional[LLMTypeEnum] = None, **default_params: Any):
        self.model_name = model_name
        self.default_params = default_params
        self.model_type: Optional[LLMTypeEnum] = model_type
        self.model_client = None

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
    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        pass

    @abstractmethod
    async def achat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
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
        pass
