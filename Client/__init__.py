from Client.asrClient import asr_client
from Client.minioClient import async_minio_client, default_minio_client


def get_asr_client():
    return asr_client


def get_minio_client(is_async: bool = False):
    return async_minio_client if is_async else default_minio_client