from typing import Optional, Any, Dict
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from Base.RicUtils.pathUtils import find_project_root


# =========================
# Base Settings with .env
# =========================
class BaseEnvSettings(BaseSettings):
    """
    自动查找 .env 文件的基类

    所有继承此类的 settings 类都会自动从项目根目录查找 .env 文件。
    支持自定义 env_prefix 以区分不同模块的环境变量。

    使用示例：
        class MySettings(BaseEnvSettings):
            host: str = "localhost"
            port: int = 3306

            model_config = SettingsConfigDict(
                env_prefix="MY_APP_",
                extra="ignore",
            )
    """

    def __init__(self, **kwargs):
        env_file = find_project_root() / ".env"
        if not env_file.exists():
            template_file = find_project_root() / ".env.template"
            if template_file.exists():
                raise FileNotFoundError(
                    f"缺少 .env 配置文件，请根据 .env.template 文件创建后启动项目\n"
                    f"参考模板路径：{template_file}"
                )
            else:
                raise FileNotFoundError(
                    "缺少 .env 配置文件，请创建 .env 文件后启动项目"
                )
        super().__init__(_env_file=env_file, **kwargs)

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False, # 忽略大小写敏感
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
    def load_env_vars(cls, env_file: Optional[Path] = None) -> "BaseEnvSettings":
        """
        从指定的 .env 文件加载环境变量
        重新指定或者切换 .env 文件路径
        Args:
            env_file: .env 文件路径，如果为 None 则使用默认路径

        Returns:
            BaseEnvSettings 实例
        """
        if env_file is None:
            env_file = find_project_root() / ".env"

        if env_file.exists():
            return cls(_env_file=env_file)
        return cls()

    # @field_validator("*", mode="before")
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
# MySQL
# =========================
class MySQLSettings(BaseEnvSettings):
    host: Optional[str] = None
    port: Optional[int] = 3306
    user: Optional[str] = None
    password: Optional[str|int] = None
    name: Optional[str] = None
    charset: str = "utf8mb4"

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
    )


# =========================
# Email
# =========================
class EmailSettings(BaseEnvSettings):
    sender_email: Optional[str] = Field(None, alias="SENDER_EMAIL")
    password: Optional[str] = Field(None, alias="EMAIL_PASSWORD")

    model_config = SettingsConfigDict(extra="ignore")

# =========================
# LLM Basic
# =========================
class LLMSettings(BaseEnvSettings):
    timeout: float = 300.0

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        extra="ignore",
    )

# =========================
# DashScope
# =========================
class DashScopeSettings(BaseEnvSettings):
    api_url: Optional[str] = Field(None, alias="DSC_API_URL")
    api_key: Optional[str] = Field(None, alias="MY_DASHSCOPE_API_KEY")
    base_url: Optional[str] = Field(None, alias="QWEN_BASE_URL")
    default_model: Optional[str] = Field(None, alias="QWEN_DEFAULT_MODEL")
    model_config = SettingsConfigDict(extra="ignore")
    embedding_model_name: Optional[str] = Field(None, alias="QWEN_EMBEDDING_MODEL_NAME")
    asr_model_name: Optional[str] = Field(None, alias="QWEN_ASR_MODEL_NAME")
    ocr_model_name: Optional[str] = Field(None, alias="QWEN_OCR_MODEL_NAME")

# =========================
# DeepSeek
# =========================
class DeepSeekSettings(BaseEnvSettings):
    api_key: Optional[str] = Field(None, alias="DEEPSEEK_API_KEY")
    base_url: Optional[str] = Field(None, alias="DEEPSEEK_BASE_URL")
    default_model: Optional[str] = Field(None, alias="DEEPSEEK_DEFAULT_MODEL")
    model_config = SettingsConfigDict(extra="ignore")


# =========================
# Redis
# =========================
class RedisSettings(BaseEnvSettings):
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
class FFmpegSettings(BaseEnvSettings):
    path: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="FFMPEG_",
        extra="ignore",
    )


# =========================
# MinIO
# =========================
class MinIOSettings(BaseEnvSettings):
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    endpoint: Optional[str] = None
    asr_text_bucket_name: Optional[str] = Field(
        None, alias="MINIO_ASR_TEXT_BUCKET_NAME"
    )

    model_config = SettingsConfigDict(
        env_prefix="MINIO_",
        extra="ignore",
    )


# =========================
# Milvus 向量数据库
# =========================
class MilvusSettings(BaseEnvSettings):
    host: Optional[str] = None
    port: Optional[int] = 19530
    uri: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = "default"
    timeout: Optional[int] = 10
    collection_name: Optional[str] = "demo_collection"
    vector_dim: Optional[int] = 1024
    secure: Optional[bool] = False
    alias: Optional[str] = "default"

    model_config = SettingsConfigDict(
        env_prefix="MILVUS_",
        extra="ignore",
    )


# =========================
# Tencent COS
# =========================
class TencentCOSSettings(BaseEnvSettings):
    secret_id: Optional[str] = None
    secret_key: Optional[str] = None
    region: Optional[str] = None

    token: Optional[str] = None
    scheme: str = "https"
    bucket_name: Optional[str] = None

    proxy_http_ip: Optional[str] = None
    proxy_https_ip: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="TC_",
        extra="ignore",
    )

# =========================
# Base module
# =========================
class BaseModuleSettings(BaseEnvSettings):
    db_name: Optional[str] = None


    model_config = SettingsConfigDict(
        env_prefix="BASE_",
        extra="ignore",
    )

# =========================
# Neo4j
# =========================
class Neo4jSettings(BaseEnvSettings):
    uri: Optional[str] = "bolt://localhost:7687"
    user: Optional[str] = "neo4j"
    password: Optional[str] = None
    database: Optional[str] = "neo4j"

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        extra="ignore",
    )

# =========================
# Auth / JWT
# =========================
class AuthSettings(BaseEnvSettings):
    jwt_secret: Optional[str] = Field(None, alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        extra="ignore",
    )

# =========================
# TTS
# =========================
class TtsSettings(BaseEnvSettings):
    server_url: Optional[str] = "http://47.115.57.130:50000/"
    bucket_name: Optional[str] = "tts-audio-cache"

    model_config = SettingsConfigDict(
        env_prefix="TTS_",
        extra="ignore",
    )

# =========================
# App Settings
# =========================
class Settings(BaseEnvSettings):
    """
    应用程序主设置类
    聚合所有模块的 settings 类。
    """

    log_level: str = "INFO"
    default: BaseEnvSettings = Field(default_factory=BaseEnvSettings)

    mysql: MySQLSettings = Field(default_factory=MySQLSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    dashscope: DashScopeSettings = Field(default_factory=DashScopeSettings)
    deepseek: DeepSeekSettings = Field(default_factory=DeepSeekSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    ffmpeg: FFmpegSettings = Field(default_factory=FFmpegSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    tencent_cos: TencentCOSSettings = Field(default_factory=TencentCOSSettings)
    base_module: BaseModuleSettings = Field(default_factory=BaseModuleSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    tts: TtsSettings = Field(default_factory=TtsSettings)

    # 覆盖 extra="ignore" 以避免加载未知的环境变量
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
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