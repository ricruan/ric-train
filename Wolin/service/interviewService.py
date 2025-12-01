import threading

from Client.minioClient import MinioAsyncClient


class InterviewAnalysisService:
    minio_async_client = MinioAsyncClient()


    def save_file_2_minio(self,file_path):
        InterviewAnalysisService.minio_async_client.upload_file_async()
