from typing import Any, AsyncGenerator, Generator, List, Dict

from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.base.baseLlm import BaseLlm
from openai import OpenAI
from Base import settings


class QwenLlm(BaseLlm):

    def __init__(self, api_key: str, base_url: str, **default_params: Any):
        super().__init__(model_name=LLMTypeEnum.QWEN.value, model_type=LLMTypeEnum.QWEN, **default_params)
        self.init_qwen_model_by_open_ai(api_key=api_key, base_url=base_url)

    def init_qwen_model_by_open_ai(self, api_key: str, base_url: str):
        self.model_client = OpenAI(api_key=api_key, base_url=base_url, timeout=settings.llm.timeout)

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
