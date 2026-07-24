from Base.Ai.llms.qwenLlm import create_qwen_llm
from Base.Config.setting import settings

default_qwen_llm = create_qwen_llm()

__all__ = ['settings','default_qwen_llm']

