from typing import Any, Optional

from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.base.baseLlm import BaseLlm
from Base.Ai.base.baseSetting import DeepSeekConfig
from Base import settings


# noinspection PyTypeChecker
class DeepSeekLlm(BaseLlm):
    """
    DeepSeek 大语言模型实现

    使用 OpenAI 兼容接口调用 DeepSeek 模型。
    支持同步/异步调用、流式/非流式输出。
    """

    # DeepSeek 模型的上下文窗口大小（token 数）
    CONTEXT_WINDOW = {
        "deepseek-chat": 128000,
        "deepseek-coder": 128000,
        "deepseek-reasoner": 64000,
    }

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        config: Optional[DeepSeekConfig] = None,
        **default_params: Any
    ):
        """
        初始化 DeepSeek 模型

        Args:
            api_key: API 密钥
            base_url: API 基础 URL，如果为 None 则使用 DeepSeek 默认 URL
            model: 模型名称，默认为 deepseek-chat
            config: DeepSeek 配置对象
            **default_params: 默认参数
        """
        # 处理配置对象和默认参数
        api_key, base_url, model, default_params = super()._process_config(
            api_key=api_key,
            base_url=base_url,
            model=model,
            config=config,
            default_params=default_params,
            base_url_error_msg="未配置DeepSeek模型的Base_Url"
        )

        super().__init__(
            model_name=model,
            model_type=LLMTypeEnum.DEEPSEEK,
            **default_params
        )
        self.model = model or settings.deepseek.default_model
        self._api_key = api_key
        self._base_url = base_url
        self.init_openai_client(api_key=api_key, base_url=base_url, logger_name=__name__)

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
        # 默认返回 128000
        return 128000

    @property
    def supports_streaming(self) -> bool:
        """
        是否支持流式输出

        Returns:
            True 表示支持流式输出
        """
        return True


# =========================
# 便捷函数
# =========================

def create_deepseek_llm(
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    **kwargs: Any
) -> DeepSeekLlm:
    """
    便捷函数：创建 DeepSeek LLM 实例

    Args:
        api_key: API 密钥，如果为 None 则从 settings 获取
        base_url: API 基础 URL，如果为 None 则使用默认值
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大 token 数
        **kwargs: 其他参数

    Returns:
        DeepSeekLlm 实例

    """
    # 如果没有提供 api_key，尝试从 settings 获取
    if api_key is None:
        if not hasattr(settings, 'deepseek'):
            raise ValueError("DeepSeek settings not found. Please provide api_key or configure settings.")
        api_key = settings.deepseek.api_key
    base_url = base_url or settings.deepseek.base_url
    model = model or settings.deepseek.default_model

    # 创建配置对象
    config = DeepSeekConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )

    return DeepSeekLlm(config=config)


if __name__ == '__main__':

    # 示例：使用便捷函数创建
    llm = create_deepseek_llm()

    print("=== 模型信息 ===")
    info = llm.get_model_info()
    for k, v in info.items():
        print(f"{k}: {v}")

    print("\n=== 测试简单调用 ===")
    res = llm.invoke("讲一个笑话")
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
