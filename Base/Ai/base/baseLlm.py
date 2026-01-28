from abc import abstractmethod, ABC
from typing import Any, Dict, List, Generator, AsyncGenerator, Optional, Union, Type
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletionUserMessageParam

from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.base.baseSetting import LLMConfig
from Base import settings
import logging
from Base.Ai.base import UserMessages

logger = logging.getLogger(__name__)


class BaseLlm(ABC):
    """
    LLM 抽象基类

    定义所有 LLM 实现必须遵循的接口。
    """

    def __init__(
            self,
            model_name: str,
            model_type: Optional[LLMTypeEnum] = None,
            config: Optional[LLMConfig] = None,
            **default_params: Any
    ):
        """
        初始化 LLM 基类

        Args:
            model_name: 模型名称
            model_type: 模型类型枚举
            config: LLM 配置对象
            **default_params: 默认参数
        """
        self.model_name = model_name
        self.model = model_name  # 用于兼容子类
        self.model_type: Optional[LLMTypeEnum] = model_type
        self.config = config
        self.model_client: Optional[OpenAI] = None
        self.async_model_client: Optional[AsyncOpenAI] = None

        # 合并配置参数和默认参数
        if config:
            config_dict = config.to_dict()
            default_params = {**config_dict, **default_params}

        self.default_params = default_params

    @abstractmethod
    def init_model(self):
        pass

    def invoke(self, prompt: str, stream: bool = False, **kwargs: Any) -> Union[str, Generator[str, None, None]]:
        """
        同步调用模型

        Args:
            prompt: 提示文本
            stream: 是否使用流式输出（默认 False）
            **kwargs: 额外参数（会覆盖默认配置）

        Returns:
            流式模式: 生成器，逐个返回文本片段
            非流式模式: 完整的响应文本

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs, stream=stream)
            response = self.model_client.chat.completions.create(
                messages=[ChatCompletionUserMessageParam(content=prompt, role='user')],
                **params
            )
            if stream:

                return self._handle_stream_response(response)
            else:
                return self._handle_response(response)

        except Exception as e:
            logger.error(
                f"Invoke 调用失败: {e}", exc_info=True
            )
            raise

    async def ainvoke(self, prompt: str, stream: bool = False, **kwargs: Any) -> Union[str, AsyncGenerator[str, None]]:
        """
        异步调用模型

        Args:
            prompt: 提示文本
            stream: 是否使用流式输出（默认 False）
            **kwargs: 额外参数（会覆盖默认配置）

        Returns:
            流式模式: 异步生成器，逐个返回文本片段
            非流式模式: 完整的响应文本
        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs, stream=stream)
            response = await self.async_model_client.chat.completions.create(
                messages=[UserMessages(prompt=prompt)],
                **params
            )

            if stream:
                return self._handle_async_stream_response(response)
            else:
                return await self._handle_async_response(response)

        except Exception as e:
            logger.error(
                f"AInvoke 调用失败: {e}", exc_info=True
            )
            raise

    def chat(
            self,
            messages: List[Union[Dict[str, str], Any]],
            stream: bool = False,
            **kwargs: Any
    ) -> Union[str, Generator[str, None, None]]:
        """
        对话模式同步调用

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            stream: 是否使用流式输出（默认 False）
            **kwargs: 额外参数（会覆盖默认配置）

        Returns:
            流式模式: 生成器，逐个返回文本片段
            非流式模式: 完整的响应文本

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs, stream=stream)
            response = self.model_client.chat.completions.create(
                messages=messages,
                **params
            )
            if stream:
                return self._handle_stream_response(response)
            else:
                return self._handle_response(response)

        except Exception as e:
            logger.error(
                f"Chat 调用失败: {e}", exc_info=True
            )
            raise

    async def achat(
            self,
            messages: List[Union[Dict[str, str], Any]],
            stream: bool = False,
            **kwargs: Any
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        对话模式异步调用

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            stream: 是否使用流式输出（默认 False）
            **kwargs: 额外参数（会覆盖默认配置）

        Returns:
            流式模式: 异步生成器，逐个返回文本片段
            非流式模式: 完整的响应文本

        Raises:
            Exception: 调用失败时抛出异常
        """
        try:
            params = self._prepare_params(**kwargs, stream=stream)
            response = await self.async_model_client.chat.completions.create(
                messages=messages,
                **params
            )

            if stream:
                return self._handle_async_stream_response(response)
            else:
                return await self._handle_async_response(response)

        except Exception as e:
            logger.error(
                f"AChat 调用失败: {e}", exc_info=True
            )
            raise

    @staticmethod
    def _handle_response(response) -> str:
        """
        处理非流式响应（子类可重写）

        Args:
            response: OpenAI 响应对象

        Returns:
            响应文本
        """
        content = response.choices[0].message.content
        logger.debug(
            f"响应内容: {content[:100] if content else 'empty'}..."
        )
        return content

    def _handle_stream_response(self, stream) -> Generator[str, None, None]:
        """
        处理同步流式响应（子类可重写）

        Args:
            stream: 流式响应对象

        Yields:
            文本片段
        """
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                logger.debug(f"同步流式片段: {content[:50]}...")
                yield content

    @staticmethod
    async def _handle_async_response(response) -> str:
        """
        处理异步非流式响应（子类可重写）

        Args:
            response: OpenAI 异步响应对象

        Returns:
            响应文本
        """
        content = response.choices[0].message.content
        logger.debug(
            f"异步响应内容: {content[:100] if content else 'empty'}..."
        )
        return content

    async def _handle_async_stream_response(self, stream) -> AsyncGenerator[str, None]:
        """
        处理异步流式响应（子类可重写）

        Args:
            stream: 异步流式响应对象

        Yields:
            文本片段
        """
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                logger.debug(f"异步流式片段: {content[:50]}...")
                yield content

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        pass

    @property
    @abstractmethod
    def context_window(self) -> int:
        """获取模型的上下文窗口大小"""
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            包含模型信息的字典，包含模型名称、类型、上下文窗口等
        """
        return {
            "model_name": self.model_name,
            "model_type": self.model_type.value if self.model_type else None,
            "context_window": self.context_window,
            "supports_streaming": self.supports_streaming,
        }

    def init_openai_client(self, api_key: str, base_url: str):
        """
        初始化 OpenAI 兼容客户端（同步和异步）

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
        """
        timeout = self.default_params.get('timeout', settings.llm.timeout if hasattr(settings, 'llm') else 30.0)

        self.model_client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.async_model_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

        logger.info(
            f"模型初始化成功，"
            f"模型: {self.model_name}, "
            f"Base URL: {base_url}, "
            f"超时: {timeout}s"
        )

    @staticmethod
    def _process_config(
            api_key: str,
            base_url: str,
            model: str,
            config: Optional[Type[LLMConfig]],
            default_params: Dict[str, Any],
            base_url_error_msg: str
    ) -> tuple:
        """
        处理配置对象和参数

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            config: 配置类实例
            default_params: 默认参数字典
            base_url_error_msg: 当缺少 base_url 时的错误消息

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
            raise ValueError(base_url_error_msg)

        return api_key, base_url, model, default_params

    @property
    def base_url_error_msg(self):
        return f"未配置{self.model_type.value}模型的Base_Url"

    def _prepare_params(self, **kwargs: Any) -> Dict[str, Any]:
        """
        准备调用参数（common 私有部分）

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

        params.setdefault("model", self.model_name)
        logger.info(f"调用参数: {params}")
        return params
