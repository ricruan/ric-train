from Base.Ai.llms.qwenLlm import create_qwen_llm
from Base.Config.logConfig import setup_logging
from Base.Config.setting import settings

setup_logging()

default_qwen_llm = create_qwen_llm()

__all__ = ['settings','default_qwen_llm']

