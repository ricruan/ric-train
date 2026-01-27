from typing import Any, Dict, Optional, Generator, List
import logging

from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.base.baseLlm import BaseLlm
from Base.Ai.base.baseSetting import DashScopeConfig
from Base import settings

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
            api_key=api_key,
            base_url=base_url,
            model=model,
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
            if kwargs.get("enable_thinking", False):
                kwargs['stream'] = True
                # kwargs['stream_options'] = {"include_usage": True}
            extra_body = {
                "enable_thinking": kwargs.get("enable_thinking", False)
            }
            del kwargs["enable_thinking"]
            return {**kwargs, "extra_body": extra_body}
        else:
            return kwargs

    def _handle_stream_with_thinking(self, stream) -> Generator[Dict[str, str], None, None]:
        """
        处理带思考过程的流式响应

        Args:
            stream: 流式响应对象

        Yields:
            字典，包含:
            - type: "reasoning" 或 "content"
            - content: 对应的内容
        """
        reasoning_content = ""  # 完整思考过程
        answer_content = ""  # 完整回复
        is_answering = False  # 是否进入回复阶段

        for chunk in stream:
            if not chunk.choices:
                # 处理 usage 信息
                if hasattr(chunk, 'usage') and chunk.usage:
                    logger.debug(f"Stream Usage: {chunk.usage}")
                continue

            delta = chunk.choices[0].delta

            # 处理思考过程
            if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                if not is_answering:
                    logger.debug(f"Thinking 片段: {delta.reasoning_content[:50]}...")
                reasoning_content += delta.reasoning_content
                yield {"type": "reasoning", "content": delta.reasoning_content}

            # 处理回复内容
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    is_answering = True
                    logger.debug("进入回复阶段")
                    yield {"type": "separator"}  # 标记从思考转到回复
                logger.debug(f"Content 片段: {delta.content[:50]}...")
                answer_content += delta.content
                yield {"type": "content", "content": delta.content}

    def invoke(
        self,
        prompt: str,
        stream: bool = False,
        **kwargs: Any
    ):
        """
        同步调用模型（重写基类方法以支持思考过程）

        Args:
            prompt: 提示文本
            stream: 是否使用流式输出（默认 False）
            **kwargs: 额外参数（会覆盖默认配置），支持 enable_thinking

        Returns:
            - 非思考模式：与基类相同
            - 思考模式（enable_thinking=True 且 stream=True）：生成器，返回 {"type": "reasoning"/"content"/"separator", "content": "..."}
        """
        enable_thinking = kwargs.pop("enable_thinking", False)

        if enable_thinking and stream:
            # 思考模式：强制使用流式
            kwargs["enable_thinking"] = True
            params = self._prepare_params(**kwargs)
            response = self.model_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            return self._handle_stream_with_thinking(response)
        else:
            # 调用基类方法
            if enable_thinking:
                kwargs["enable_thinking"] = enable_thinking
            return super().invoke(prompt, stream=stream, **kwargs)


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
    llm = create_qwen_llm()

    print("=== 模型信息 ===")
    info = llm.get_model_info()
    for k, v in info.items():
        print(f"{k}: {v}")

    # print("\n=== 测试思考模式 ===")
    # res = llm.invoke("讲一个笑话", enable_thinking=True, model="qwen-plus", stream=True)
    # print("\n" + "=" * 20 + "思考过程" + "=" * 20)
    # for chunk in res:
    #     if chunk["type"] == "reasoning":
    #         print(chunk["content"], end="", flush=True)
    #     elif chunk["type"] == "separator":
    #         print("\n" + "=" * 20 + "完整回复" + "=" * 20)
    #     elif chunk["type"] == "content":
    #         print(chunk["content"], end="", flush=True)
    # print()  # 换行

    print("\n=== 测试非思考模式 ===")
    res = llm.invoke("讲一个笑话", model="qwen-plus")
    print(res)

    # print("\n=== 测试对话模式 ===")
    # messages = [
    #     {"role": "system", "content": "你是一个有帮助的助手"},
    #     {"role": "user", "content": "请用一句话介绍Python"}
    # ]
    # res = llm.chat(messages)
    # print(res)
    #
    # print("\n=== 测试流式输出 ===")
    # for chunk in llm.stream("请写一首关于春天的诗"):
    #     print(chunk, end="", flush=True)
    # print()
