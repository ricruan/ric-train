from Client.allPublic import get_asr_client
from Wolin.service.base import service_logger

logger = service_logger

class AsrService:
    client = get_asr_client()

    def audio_2_text_handle(self, file_path: str | list[str], max_workers: int = 50):
        """
        使用线程池并发运行 ASR 函数，并保持原始顺序

        Args:
            file_path: 单个文件路径或文件路径列表
            max_workers: 最大并发线程数

        Returns:
            List[str]: 按原始顺序排列的 ASR 结果列表
        """
        ordered_results = self.client.audio_2_text(file_path=file_path,max_workers=max_workers)

        # temp_file_path = ''
        # with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
        #     # 写入每行（添加换行符）
        #     for line in ordered_results:
        #         tmp_file.write(line + '\n')
        #
        #     # 刷新确保内容写入磁盘（某些场景需要）
        #     tmp_file.flush()
        #     temp_file_path = tmp_file.name
        #
        # MinioClient().upload_file(bucket_name="audio-text",
        #                           object_name=f'{self.get_username}/{self.company_name or get_current_date()}.txt',
        #                           file_path=temp_file_path)
        #
        # os.unlink(temp_file_path)



