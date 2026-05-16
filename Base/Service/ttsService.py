import hashlib
import logging
import os
from typing import Optional

from Base.Client.ttsClient import TtsClient
from Base.Client.minioClient import MinioClient
from Base.Config.setting import settings

logger = logging.getLogger(__name__)


class TtsService:
    """
    TTS 缓存服务：通过 MinIO 持久化已生成的音频，避免重复合成相同内容。
    返回值为 MinIO object_name，调用方可自行生成预签名 URL。
    """

    def __init__(self, voice: str = "中文女", url_expiry_hours: float = 24):
        tts_conf = settings.tts.model_dump()
        self.bucket_name = tts_conf.get("bucket_name") or "tts-audio-cache"
        self.voice = voice
        self.url_expiry_hours = url_expiry_hours
        self._tts_client = TtsClient()
        self._minio_client = MinioClient()
        self._ensure_bucket()

    # ──────────────── 公开方法 ────────────────

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> Optional[str]:
        """
        合成语音，优先从 MinIO 缓存中获取。
        返回 MinIO object_name，调用方可自行生成预签名 URL。

        :param text: 合成文本
        :param voice: 音色，不传则使用默认音色
        :param kwargs: 透传给 TtsClient.synthesize 的额外参数
        :return: MinIO object_name（格式：{voice}/{md5}.wav），失败时返回 None
        """
        voice = voice or self.voice
        object_name = self._build_object_name(voice, text)

        # 1. 检查 MinIO 缓存是否存在
        stat = self._minio_client.stat_object(self.bucket_name, object_name)
        if stat:
            logger.info(f"TTS 缓存命中: voice={voice}, object_name={object_name}")
            return object_name

        # 2. 缓存未命中，调用 TTS 生成
        logger.info(f"TTS 缓存未命中，开始合成: voice={voice}")
        try:
            local_path = self._tts_client.synthesize(text=text, voice=voice, **kwargs)
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            return None

        if not local_path:
            return None

        # 3. 上传到 MinIO 缓存
        if not self._upload_to_minio(local_path, object_name):
            return None

        # 4. 清理本地临时文件
        try:
            os.unlink(local_path)
        except OSError:
            pass

        return object_name

    # ──────────────── 内部方法 ────────────────

    def _ensure_bucket(self):
        """确保缓存 bucket 存在。"""
        if not self._minio_client.bucket_exists(self.bucket_name):
            self._minio_client.make_bucket(self.bucket_name)

    def _build_object_name(self, voice: str, text: str) -> str:
        """根据 voice + text 生成 MinIO 对象名：{voice}/{md5}.wav"""
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        return f"{voice}/{text_hash}.wav"

    def _upload_to_minio(self, local_path: str, object_name: str) -> bool:
        """将本地音频上传到 MinIO 缓存。返回是否成功。"""
        try:
            self._minio_client.upload_file(self.bucket_name, object_name, local_path)
            return True
        except Exception as e:
            logger.error(f"TTS 缓存上传失败: {e}")
            return False


def synthesize_tts(text: str, voice: str = "中文女", **kwargs) -> Optional[str]:
    """
    TTS 合成便捷函数，自动使用 MinIO 缓存。

    :param text: 合成文本
    :param voice: 音色
    :param kwargs: 透传给 TtsClient.synthesize 的额外参数
    :return: MinIO object_name（格式：{voice}/{md5}.wav），失败时返回 None
    """
    return TtsService(voice=voice).synthesize(text=text, **kwargs)

