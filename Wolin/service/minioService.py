import os
from Base.Client import get_minio_client


class MinIOService:
    minio_client = get_minio_client(is_async=True)


    def save_audio_text_by_str_list(self,ordered_results: list[str],minio_object_name: str,bucket_name: str = None):
        """
        将  str of list 存入 MinIo
        """
        if not bucket_name:
            bucket_name = os.getenv("MINIO_ASR_TEXT_BUCKET_NAME")
        if bucket_name and minio_object_name:
            self.minio_client.str_list_2_minio(str_list=ordered_results,
                                               bucket_name=bucket_name,
                                               object_name=minio_object_name)


minio_service = MinIOService()