import hashlib
import pytest
from unittest.mock import MagicMock, patch
from Base.Service.ttsService import TtsService, synthesize_tts


class TestTtsServiceSynthesize:
    """synthesize() 应返回 object_name 而非完整预签名 URL"""

    def setup_method(self):
        self.mock_tts_client = MagicMock()
        self.mock_minio_client = MagicMock()
        self.tts_patcher = patch("Base.Service.ttsService.TtsClient", return_value=self.mock_tts_client)
        self.minio_patcher = patch("Base.Service.ttsService.MinioClient", return_value=self.mock_minio_client)
        self.mock_tts_cls = self.tts_patcher.start()
        self.mock_minio_cls = self.minio_patcher.start()
        self.service = TtsService(voice="中文女")

    def teardown_method(self):
        self.tts_patcher.stop()
        self.minio_patcher.stop()

    def test_synthesize_returns_object_name_format(self):
        """返回值应为 object_name 格式：voice/md5.wav"""
        self.mock_minio_client.stat_object.return_value = None  # 缓存未命中
        self.mock_tts_client.synthesize.return_value = "/tmp/test.wav"
        self.mock_minio_client.get_presigned_url.return_value = "http://presigned-url"

        result = self.service.synthesize("你好，世界")

        # 返回值必须是 object_name，不是 URL
        assert result is not None
        assert result.startswith("中文女/")
        assert result.endswith(".wav")
        assert not result.startswith("http")
        self.mock_minio_client.upload_file.assert_called_once()

    def test_synthesize_cache_hit_returns_object_name(self):
        """缓存命中时也应返回 object_name"""
        self.mock_minio_client.stat_object.return_value = MagicMock()  # 缓存命中
        self.mock_minio_client.get_presigned_url.return_value = "http://presigned-url"

        result = self.service.synthesize("你好")

        assert result is not None
        assert not result.startswith("http")
        assert result.startswith("中文女/")

    def test_synthesize_returns_none_on_failure(self):
        """TTS 合成失败应返回 None"""
        self.mock_minio_client.stat_object.return_value = None
        self.mock_tts_client.synthesize.side_effect = Exception("TTS failed")

        result = self.service.synthesize("你好")
        assert result is None


    def test_synthesize_tts_calls_service(self):
        """synthesize_tts 便捷函数委托给 TtsService"""
        with patch("Base.Service.ttsService.TtsService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.synthesize.return_value = "中文女/abc123.wav"
            mock_service_cls.return_value = mock_service

            result = synthesize_tts("测试文本", voice="中文女")

            assert result == "中文女/abc123.wav"
            mock_service.synthesize.assert_called_once_with(text="测试文本")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
