from typing import Optional

from pydantic import BaseModel, Field
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
# DashScope
# =========================
class DashScopeSettings(BaseSettings):
    api_url: str = Field(..., alias="DSC_API_URL")
    api_key: str = Field(..., alias="DASHSCOPE_API_KEY")

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
# App Settings
# =========================
class Settings(BaseSettings):
    log_level: str = "INFO"

    mysql: MySQLSettings = Field(default_factory=MySQLSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    dashscope: DashScopeSettings = Field(default_factory=DashScopeSettings)
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