"""
LLM 配置类

提供统一的大语言模型配置管理。
"""
from dataclasses import dataclass, field
from typing import Optional, Any, Dict

from Base import settings


@dataclass
class LLMConfig:
    """
    LLM 配置类

    包含所有常见的大语言模型配置参数。
    """
    model: str
    """模型名称"""

    api_key: str
    """API 密钥"""

    base_url: str
    """API 基础 URL"""

    temperature: Optional[float] = None
    """温度参数，控制随机性，范围 0.0-2.0"""

    max_tokens: Optional[int] = None
    """最大生成的 token 数"""

    top_p: Optional[float] = None
    """nucleus 采样，控制生成文本的多样性"""

    frequency_penalty: Optional[float] = None
    """频率惩罚，减少重复内容"""

    presence_penalty: Optional[float] = None
    """存在惩罚，鼓励讨论新话题"""

    stop: Optional[list[str]] = None
    """停止序列"""

    timeout: float = settings.llm.timeout
    """请求超时时间（秒）"""

    additional_params: Dict[str, Any] = field(default_factory=dict)
    """其他额外参数"""

    def to_dict(self) -> Dict[str, Any]:
        """
        将配置转换为字典，过滤掉 None 值

        Returns:
            配置字典
        """
        result = {}
        for key, value in self.__dict__.items():
            if value is not None and key != 'additional_params':
                result[key] = value
        result.update(self.additional_params)
        return result

    @classmethod
    def from_settings(cls, settings_dict: Dict[str, Any]) -> "LLMConfig":
        """
        从字典创建配置

        Args:
            settings_dict: 配置字典

        Returns:
            LLMConfig 实例
        """
        return cls(**settings_dict)


@dataclass
class DashScopeConfig(LLMConfig):
    """
    DashScope (通义千问) 配置

    专用于 DashScope API 的配置类。
    """

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None, **kwargs):
        """
        初始化 DashScope 配置

        Args:
            api_key: DashScope API 密钥
            model: 模型名称
            base_url: API 基础 URL，默认为 DashScope 兼容模式
            **kwargs: 其他参数
        """
        base_url = base_url or settings.dashscope.base_url
        api_key = api_key or settings.dashscope.api_key
        model = model or settings.dashscope.default_model

        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )


@dataclass
class DeepSeekConfig(LLMConfig):
    """
    DeepSeek (深度求索) 配置

    专用于 DeepSeek API 的配置类。
    """

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None, **kwargs):
        """
        初始化 DeepSeek 配置

        Args:
            api_key: DeepSeek API 密钥
            model: 模型名称
            base_url: API 基础 URL，默认为 DeepSeek 官方 API 地址
            **kwargs: 其他参数
        """
        base_url = base_url or settings.deepseek.base_url
        api_key = api_key or settings.deepseek.api_key
        model = model or settings.deepseek.default_model

        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )
