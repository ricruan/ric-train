from Client import get_asr_client
from Wolin.service.base import service_logger

logger = service_logger

class AsrService:
    asr_client = get_asr_client()

    def audio_2_text_handle(self, file_path: str | list[str], max_workers: int = 50):
        """
        使用线程池并发运行 ASR 函数，并保持原始顺序

        Args:
            file_path: 单个文件路径或文件路径列表
            max_workers: 最大并发线程数
        Returns:
            List[str]: 按原始顺序排列的 ASR 结果列表
        """
        ordered_results = self.asr_client.audio_2_text(file_path=file_path, max_workers=max_workers)
        return ordered_results


asr_service = AsrService()
