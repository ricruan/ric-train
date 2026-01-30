from typing import Optional, Any, Dict
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from Base.RicUtils.pathUtils import find_project_root


# =========================
# MySQL
# =========================
class MySQLSettings(BaseSettings):
    host: str
    port: int = 3306
    user: str
    password: str
    name: str
    charset: str = "utf8mb4"

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
    )


# =========================
# Email
# =========================
class EmailSettings(BaseSettings):
    sender_email: Optional[str] = Field(None, alias="SENDER_EMAIL")
    password: str = Field(..., alias="EMAIL_PASSWORD")

    model_config = SettingsConfigDict(extra="ignore")

# =========================
# LLM Basic
# =========================
class LLMSettings(BaseSettings):
    timeout: float = 30.0

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        extra="ignore",
    )

# =========================
# DashScope
# =========================
class DashScopeSettings(BaseSettings):
    api_url: str = Field(..., alias="DSC_API_URL")
    api_key: str = Field(..., alias="DASHSCOPE_API_KEY")
    base_url: str = Field(..., alias="QWEN_BASE_URL")
    default_model: str = Field(..., alias="QWEN_DEFAULT_MODEL")
    model_config = SettingsConfigDict(extra="ignore")


# =========================
# DeepSeek
# =========================
class DeepSeekSettings(BaseSettings):
    api_key: str = Field(..., alias="DEEPSEEK_API_KEY")
    base_url: str = Field(..., alias="DEEPSEEK_BASE_URL")
    default_model: str = Field(..., alias="DEEPSEEK_DEFAULT_MODEL")
    model_config = SettingsConfigDict(extra="ignore")


# =========================
# Redis
# =========================
class RedisSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        extra="ignore",
    )


# =========================
# FFmpeg
# =========================
class FFmpegSettings(BaseSettings):
    path: str

    model_config = SettingsConfigDict(
        env_prefix="FFMPEG_",
        extra="ignore",
    )


# =========================
# MinIO
# =========================
class MinIOSettings(BaseSettings):
    access_key: str
    secret_key: str
    endpoint: str
    asr_text_bucket_name: Optional[str] = Field(
        None, alias="MINIO_ASR_TEXT_BUCKET_NAME"
    )

    model_config = SettingsConfigDict(
        env_prefix="MINIO_",
        extra="ignore",
    )


# =========================
# Tencent COS
# =========================
class TencentCOSSettings(BaseSettings):
    secret_id: str
    secret_key: str
    region: str

    token: Optional[str] = None
    scheme: str = "https"
    bucket_name: str

    proxy_http_ip: Optional[str] = None
    proxy_https_ip: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="TC_",
        extra="ignore",
    )


# =========================
# Default Settings
# =========================
class DefaultSettings(BaseSettings):
    """
    默认设置类，自动加载 .env 文件中的所有额外变量

    使用 extra="allow" 接受任意环境变量。
    提供便捷的字典式访问和动态字段查询。
    """

    model_config = SettingsConfigDict(
        env_file=find_project_root() / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # 允许额外的字段
    )

    def __getitem__(self, key: str) -> Any:
        """字典式访问环境变量"""
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        """检查环境变量是否存在"""
        return key in self.model_dump()

    def get(self, key: str, default: Any = None) -> Any:
        """
        安全获取环境变量值

        Args:
            key: 环境变量名
            default: 默认值，如果变量不存在则返回该值

        Returns:
            环境变量值或默认值
        """
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """
        将所有设置转换为字典

        Returns:
            包含所有环境变量的字典
        """
        return self.model_dump()

    @classmethod
    def load_env_vars(cls, env_file: Optional[Path] = None) -> "DefaultSettings":
        """
        从指定的 .env 文件加载环境变量

        Args:
            env_file: .env 文件路径，如果为 None 则使用默认路径

        Returns:
            DefaultSettings 实例
        """
        if env_file is None:
            env_file = find_project_root() / ".env"

        if env_file.exists():
            return cls(_env_file=env_file)
        return cls()

    @field_validator("*", mode="before")
    @classmethod
    def parse_env_vars(cls, v: Any, info) -> Any:
        """
        环境变量值解析器

        自动处理常见的数据类型转换。
        """
        if isinstance(v, str):
            # 尝试转换为布尔值
            if v.lower() in ("true", "yes", "1"):
                return True
            if v.lower() in ("false", "no", "0"):
                return False

            # 尝试转换为数字
            try:
                return int(v)
            except ValueError:
                try:
                    return float(v)
                except ValueError:
                    pass

        return v


# =========================
# App Settings
# =========================
class Settings(BaseSettings):
    """应用程序主设置类"""

    log_level: str = "INFO"
    default: DefaultSettings = Field(default_factory=DefaultSettings)

    mysql: MySQLSettings = Field(default_factory=MySQLSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    dashscope: DashScopeSettings = Field(default_factory=DashScopeSettings)
    deepseek: DeepSeekSettings = Field(default_factory=DeepSeekSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    ffmpeg: FFmpegSettings = Field(default_factory=FFmpegSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    tencent_cos: TencentCOSSettings = Field(default_factory=TencentCOSSettings)

    model_config = SettingsConfigDict(
        env_file=find_project_root() / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False, # 大小写敏感？
        extra="ignore",
    )


# =========================
# Singleton
# =========================
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()