import threading
from pathlib import Path
from Client.minioClient import MinioAsyncClient
from RicUtils.decoratorUtils import EarlyStop, params_handle_4c
from Wolin.interviewAnalysis import InterviewAnalysis


class InterviewAnalysisService:
    minio_async_client = MinioAsyncClient()

    def __init__(self,instance: InterviewAnalysis = None):
        if instance:
            self.instance = instance


    def _precondition(self):
        if not InterviewAnalysisService.minio_async_client.is_active:
            raise EarlyStop
        if not self.instance:
            raise EarlyStop

    @params_handle_4c(_precondition)
    def save_origin_file_2_minio(self):
        user_name = self.instance.get_username
        resume_file = self.instance.resume_file
        audio_file = self.instance.audio_file
        minio_client = InterviewAnalysisService.minio_async_client

        if resume_file:
            minio_client.upload_file_async(bucket_name='resumes',
                                  object_name=user_name + '/' + Path(resume_file).name,
                                  file_path=resume_file)

        if audio_file:
            minio_client.upload_file_async(bucket_name='audios',
                                           object_name=user_name + '/' + Path(audio_file).name,
                                           file_path=resume_file)

    @params_handle_4c(_precondition)
    def save_other_file_2_minio(self):
        report_file = self.instance.report_path
        user_name = self.instance.get_username
        minio_client = InterviewAnalysisService.minio_async_client

        if report_file:
            minio_client.upload_file_async(bucket_name='resumes',
                                  object_name=user_name + '/' + Path(report_file).name,
                                  file_path=report_file)
        pass