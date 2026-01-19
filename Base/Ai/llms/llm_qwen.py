from typing import Any, AsyncGenerator, Generator, List, Dict

from Base.Ai.base.baseLlm import BaseLlm


class QwenLlm(BaseLlm):

    def __init__(self, model_name: str, **default_params: Any):
        super().__init__(model_name, **default_params)
        self.model_name = model_name
        self.default_params = default_params

    def init_model(self):
        pass

    @property
    def context_window(self) -> int:
        return 10

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        pass

    async def ainvoke(self, prompt: str, **kwargs: Any) -> str:
        pass

    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        pass

    async def achat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        pass

    def stream(self, prompt: str, **kwargs: Any) -> Generator[str, None, None]:
        pass

    async def astream(self, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        pass

    @property
    def supports_streaming(self) -> bool:
        return True


