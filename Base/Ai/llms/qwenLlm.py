from typing import Any, Dict, Optional, Generator, List
import logging

from Base.Ai.base import UserMessages, SystemMessages
from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.base.baseLlm import BaseLlm
from Base.Ai.base.baseSetting import DashScopeConfig
from Base.Config.setting import settings

logger = logging.getLogger(__name__)


# noinspection PyTypeChecker
class QwenLlm(BaseLlm):
    """
    Qwen 大语言模型实现

    使用 OpenAI 兼容接口调用 Qwen 模型。
    支持同步/异步调用、流式/非流式输出。
    """

    # Qwen 模型的上下文窗口大小（token 数）
    CONTEXT_WINDOW = {
        "qwen-turbo": 8192,
        "qwen-plus": 32768,
        "qwen-max": 32768,
        "qwen-long": 1000000,
        "qwen2.5-72b-instruct": 131072,
        "qwen2.5-32b-instruct": 131072,
        "qwen2.5-14b-instruct": 131072,
        "qwen2.5-7b-instruct": 131072,
        "qwen-vl-plus": 8192,
        "qwen-vl-max": 32768,
    }

    def __init__(
            self,
            api_key: str = None,
            base_url: str = None,
            model: str = None,
            config: Optional[DashScopeConfig] = None,
            **default_params: Any
    ):
        """
        初始化 Qwen 模型

        Args:
            api_key: API 密钥
            base_url: API 基础 URL，如果为 None 则使用 DashScope 默认 URL
            model: 模型名称，默认为 qwen-plus
            config: DashScope 配置对象
            **default_params: 默认参数
        """
        # 处理配置对象和默认参数
        api_key, base_url, model, default_params = super()._process_config(
            api_key=api_key or settings.dashscope.api_key,
            base_url=base_url or settings.dashscope.base_url,
            model=model or settings.dashscope.default_model,
            config=config,
            default_params=default_params,
            base_url_error_msg="未配置Qwen模型的Base_Url"
        )

        super().__init__(
            model_name=model,
            model_type=LLMTypeEnum.QWEN,
            **default_params
        )
        self.model = model or settings.dashscope.default_model
        self._api_key = api_key
        self._base_url = base_url
        self.init_openai_client(api_key=api_key, base_url=base_url)

    def init_model(self):
        """初始化模型（已通过 init_openai_client 实现）"""
        pass

    @property
    def context_window(self) -> int:
        """获取上下文窗口大小"""
        # 尝试从模型名称获取上下文窗口大小
        for key, size in self.CONTEXT_WINDOW.items():
            if key in self.model.lower():
                return size
        # 默认返回 32768
        return 32768

    @property
    def supports_streaming(self) -> bool:
        """
        是否支持流式输出

        Returns:
            True 表示支持流式输出
        """
        return True

    def _prepare_params(self, **kwargs: Any) -> Dict[str, Any]:
        kwargs = super()._prepare_params(**kwargs)
        if "enable_thinking" in kwargs:
            enable_thinking = kwargs.get("enable_thinking", False)
            if enable_thinking:
                kwargs['stream'] = True
            extra_body = {
                "enable_thinking": enable_thinking
            }
            # 保存到 default_params 中，供后续使用
            self.default_params['enable_thinking'] = enable_thinking
            del kwargs["enable_thinking"]
            return {**kwargs, "extra_body": extra_body}
        else:
            return kwargs

    @staticmethod
    def _process_thinking_chunk(chunk, log_prefix: str):
        """
        处理思考模式的单个 chunk

        Args:
            chunk: 流式响应 chunk
            log_prefix: 日志前缀（如 "Stream", "Async Stream"）

        Yields:
            字典 {"type": "reasoning"/"content", "content": "..."}
        """
        if not chunk.choices:
            # 处理 usage 信息
            if hasattr(chunk, 'usage') and chunk.usage:
                logger.debug(f"{log_prefix} Usage: {chunk.usage}")
            return

        delta = chunk.choices[0].delta

        # 处理思考过程
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            content = delta.reasoning_content
            logger.debug(f"{log_prefix} Thinking 片段: {content[:50]}...")
            yield {"type": "reasoning", "content": content}

        # 处理回复内容
        if hasattr(delta, "content") and delta.content:
            content = delta.content
            logger.debug(f"{log_prefix} Content 片段: {content[:50]}...")
            yield {"type": "content", "content": content}

    def _handle_stream_response(self, stream) -> Generator:
        """
        重写基类的流式响应处理方法，支持思考过程

        Args:
            stream: 流式响应对象

        Yields:
            - 普通模式：文本片段（字符串）
            - 思考模式：字典 {"type": "reasoning"/"content", "content": "..."}
        """
        enable_thinking = self.default_params.get('enable_thinking', False)

        if enable_thinking:
            # 思考模式：返回带类型的字典
            for chunk in stream:
                yield from self._process_thinking_chunk(chunk, "Stream")
        else:
            # 普通模式：调用基类的默认处理
            yield from super()._handle_stream_response(stream)

    async def _handle_async_stream_response(self, stream):
        """
        重写基类的异步流式响应处理方法，支持思考过程

        Args:
            stream: 异步流式响应对象

        Yields:
            - 普通模式：文本片段（字符串）
            - 思考模式：字典 {"type": "reasoning"/"content", "content": "..."}
        """
        enable_thinking = self.default_params.get('enable_thinking', False)

        if enable_thinking:
            # 思考模式：返回带类型的字典
            async for chunk in stream:
                for result in self._process_thinking_chunk(chunk, "Async Stream"):
                    yield result
        else:
            # 普通模式：调用基类的默认处理
            async for chunk in super()._handle_async_stream_response(stream):
                yield chunk


# =========================
# 便捷函数
# =========================

def create_qwen_llm(
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs: Any
) -> QwenLlm:
    """
    便捷函数：创建 Qwen LLM 实例

    Args:
        api_key: API 密钥，如果为 None 则从 settings 获取
        base_url: API 基础 URL，如果为 None 则使用默认值
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大 token 数
        **kwargs: 其他参数

    Returns:
        QwenLlm 实例

    """
    # 如果没有提供 api_key，尝试从 settings 获取
    if api_key is None:
        if not hasattr(settings, 'dashscope'):
            raise ValueError("DashScope settings not found. Please provide api_key or configure settings.")
        api_key = settings.dashscope.api_key
    base_url = base_url or settings.dashscope.base_url
    model = model or settings.dashscope.default_model

    # 创建配置对象
    config = DashScopeConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )

    return QwenLlm(config=config)


if __name__ == '__main__':

    # 示例：使用便捷函数创建
    llm = QwenLlm()

    print("=== 模型信息 ===")
    info = llm.get_model_info()
    for k, v in info.items():
        print(f"{k}: {v}")

    # 测试思考模式
    print("\n=== 测试思考模式 ===")
    res = llm.invoke("讲一个笑话", enable_thinking=True, model="qwen-plus", stream=True)
    print("\n" + "=" * 20 + "思考过程" + "=" * 20)
    for chunk in res:
        if chunk["type"] == "reasoning":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "separator":
            print("\n" + "=" * 20 + "完整回复" + "=" * 20)
        elif chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
    print()  # 换行

    # 测试非思考模式（非流式）
    # print("\n=== 测试非思考模式（非流式）===")
    # # res = llm.invoke("讲一个笑话", model="qwen-plus")
    # res = llm.chat([SystemMessages("你是一个有帮助的助手"), UserMessages("请用一句话介绍Python")])
    # print(res)
    #
    # # 测试非思考模式（流式）
    # print("\n=== 测试非思考模式（流式）===")
    # res = llm.invoke("讲一个笑话", model="qwen-plus", stream=True)
    # for chunk in res:
    #     print(chunk, end="")
    # print()  # 换行
    #
    # # 测试对话模式
    # print("\n=== 测试对话模式 ===")
    # messages = [
    #     {"role": "system", "content": "你是一个有帮助的助手"},
    #     {"role": "user", "content": "请用一句话介绍Python"}
    # ]
    # res = llm.chat(messages)
    # print(res)
    #
    # # 测试对话模式（流式）
    # print("\n=== 测试对话模式（流式）===")
    # res = llm.chat(messages, stream=True)
    # for chunk in res:
    #     print(chunk, end="")
    # print()  # 换行
