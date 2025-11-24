import asyncio
import logging
import os
import threading
from typing import Optional

from fastapi import APIRouter, UploadFile, File

from RicUtils.fileUtils import save_upload_file_to_temp
from RicUtils.httpUtils import HttpResponse
from Wolin.interviewAnalysis import InterviewAnalysis

router = APIRouter()

logger = logging.getLogger(__name__)

@router.post("/interview_analysis")
async def interview_analysis(
        audio_file: UploadFile = File(...),
        resume_file: Optional[UploadFile] = None
):
    audio_file_path = await save_upload_file_to_temp(audio_file,use_original_filename=True)
    resume_file_path = await save_upload_file_to_temp(resume_file,use_original_filename=True)

    def run_analysis():
        try:
            InterviewAnalysis(audio_file=audio_file_path, resume_file=resume_file_path).analysis()
        except Exception as e:
            logger.error(f"[后台线程] InterviewAnalysis 发生异常: {e}")
        finally:
            os.unlink(audio_file_path)
            os.unlink(resume_file_path)

    # 3. 后台启动一个线程运行它（不阻塞当前请求）
    thread = threading.Thread(target=run_analysis)
    thread.start()
    return HttpResponse.ok(msg="正在分析中...")
