from typing import Any, AsyncGenerator, Generator, List, Dict, Optional

from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.base.baseLlm import BaseLlm
from Base.Ai.base.baseSetting import DashScopeConfig
from openai import OpenAI, AsyncOpenAI
from Base import settings
import logging

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
        api_key, base_url, model, default_params = self._process_config(
            api_key=api_key,
            base_url=base_url,
            model=model,
            config=config,
            default_params=default_params
        )

        super().__init__(
            model_name=model,
            model_type=LLMTypeEnum.QWEN,
            **default_params
        )
        self.async_model_client = None
        self.model = model or settings.dashscope.default_model
        self._api_key = api_key
        self._base_url = base_url
        self.init_qwen_model_by_open_ai(api_key=api_key, base_url=base_url)

    def init_qwen_model_by_open_ai(self, api_key: str, base_url: str):
        """初始化 OpenAI 兼容客户端"""
        timeout = self.default_params.get('timeout', settings.llm.timeout if hasattr(settings, 'llm') else 30.0)

        self.model_client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.async_model_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

        logger.info(
            f"Qwen 模型初始化成功，"
            f"模型: {self.model}, "
            f"Base URL: {base_url}, "
            f"超时: {timeout}s"
        )

    @staticmethod
    def _process_config(
        api_key: str,
        base_url: str,
        model: str,
        config: Optional[DashScopeConfig],
        default_params: Dict[str, Any]
    ) -> tuple:
        """
        处理配置对象和参数

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            config: DashScope 配置对象
            default_params: 默认参数字典

        Returns:
            (api_key, base_url, model, default_params) 元组

        Raises:
            ValueError: 如果未配置必要的参数
        """
        if config:
            # 从配置对象中提取参数
            api_key = config.api_key
            base_url = base_url or config.base_url
            model = model or config.model

            # 合并配置参数到默认参数
            config_params = config.to_dict()
            # 移除不需要传递给父类的配置项
            config_params.pop('model', None)
            config_params.pop('api_key', None)
            config_params.pop('base_url', None)
            default_params = {**config_params, **default_params}
        elif base_url is None:
            raise ValueError("未配置Qwen模型的Base_Url")

        return api_key, base_url, model, default_params

    def init_model(self):
        """初始化模型（已通过 init_qwen_model_by_open_ai 实现）"""
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

    def _prepare_params(self, **kwargs: Any) -> Dict[str, Any]:
        """
        准备调用参数

        合并默认参数和传入参数，并过滤掉 None 值。

        Args:
            **kwargs: 传入的参数

        Returns:
            清理后的参数字典
        """
        params = self.default_params.copy()
        params.update(kwargs)

        # 过滤掉 None 值和不必要的参数
        params = {k: v for k, v in params.items() if v is not None}

        return params

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        """
        同步调用模型

        Args:
            prompt: 提示文本
            **kwargs: 额外参数（会覆盖默认配置）

        Returns:
            模型返回的文本

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs)
            params.setdefault("model", self.model)

            response = self.model_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                **params
            )

            content = response.choices[0].message.content
            logger.debug(f"Invoke 响应: {content[:100] if content else 'empty'}...")
            return content

        except Exception as e:
            logger.error(f"Invoke 调用失败: {e}", exc_info=True)
            raise

    async def ainvoke(self, prompt: str, **kwargs: Any) -> str:
        """
        异步调用模型

        Args:
            prompt: 提示文本
            **kwargs: 额外参数（会覆盖默认配置）

        Returns:
            模型返回的文本

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs)
            params.setdefault("model", self.model)

            response = await self.async_model_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                **params
            )

            content = response.choices[0].message.content
            logger.debug(f"AInvoke 响应: {content[:100] if content else 'empty'}...")
            return content

        except Exception as e:
            logger.error(f"AInvoke 调用失败: {e}", exc_info=True)
            raise

    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        对话模式同步调用

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 额外参数（会覆盖默认配置）

        Returns:
            模型返回的文本

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs)
            params.setdefault("model", self.model)

            response = self.model_client.chat.completions.create(
                messages=messages,
                **params
            )

            content = response.choices[0].message.content
            logger.debug(f"Chat 响应: {content[:100] if content else 'empty'}...")
            return content

        except Exception as e:
            logger.error(f"Chat 调用失败: {e}", exc_info=True)
            raise

    async def achat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        对话模式异步调用

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 额外参数（会覆盖默认配置）

        Returns:
            模型返回的文本

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs)
            params.setdefault("model", self.model)

            response = await self.async_model_client.chat.completions.create(
                messages=messages,
                **params
            )

            content = response.choices[0].message.content
            logger.debug(f"AChat 响应: {content[:100] if content else 'empty'}...")
            return content

        except Exception as e:
            logger.error(f"AChat 调用失败: {e}", exc_info=True)
            raise

    def stream(self, prompt: str, **kwargs: Any) -> Generator[str, None, None]:
        """
        同步流式调用

        Args:
            prompt: 提示文本
            **kwargs: 额外参数（会覆盖默认配置）

        Yields:
            模型返回的文本片段

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs)
            params.setdefault("model", self.model)
            params["stream"] = True

            stream = self.model_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                **params
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    logger.debug(f"Stream 片段: {content[:50]}...")
                    yield content

        except Exception as e:
            logger.error(f"Stream 调用失败: {e}", exc_info=True)
            raise

    async def astream(self, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        """
        异步流式调用

        Args:
            prompt: 提示文本
            **kwargs: 额外参数（会覆盖默认配置）

        Yields:
            模型返回的文本片段

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs)
            params.setdefault("model", self.model)
            params["stream"] = True

            stream = await self.async_model_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                **params
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    logger.debug(f"AStream 片段: {content[:50]}...")
                    yield content

        except Exception as e:
            logger.error(f"AStream 调用失败: {e}", exc_info=True)
            raise

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
    logging.basicConfig(level=logging.INFO)

    # 示例：使用便捷函数创建
    llm = create_qwen_llm()

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

