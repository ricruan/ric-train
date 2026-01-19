from abc import abstractmethod, ABC
from typing import Any, Dict, List, Generator, AsyncGenerator

class BaseLlm(ABC):
    def __init__(self, model_name: str, **default_params: Any):
        self.model_name = model_name
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