import asyncio
import logging
import os
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, Response

from RicUtils.fileUtils import save_upload_file_to_temp
from RicUtils.httpUtils import HttpResponse
from Wolin.interviewAnalysis import InterviewAnalysis
from Wolin.service.interviewService import InterviewAnalysisService

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/interview_analysis")
async def interview_analysis(
        receive_email: str,
        user_name: str,
        company_name: str,
        audio_file: UploadFile = File(...),
        resume_file: Optional[UploadFile] = None
):
    audio_file_path = await save_upload_file_to_temp(audio_file, use_original_filename=True)
    resume_file_path = await save_upload_file_to_temp(resume_file, use_original_filename=True)

    def run_analysis():
        try:
            analysis_instance = InterviewAnalysis(audio_file=audio_file_path,
                                                  resume_file=resume_file_path,
                                                  receive_email=receive_email,
                                                  user_name=user_name,
                                                  company_name=company_name)
            service = InterviewAnalysisService(analysis_instance)
            service.save_origin_file_2_minio()
            analysis_instance.analysis()
        except Exception as e:
            logger.error(f"[后台线程] InterviewAnalysis 发生异常: {e}", stack_info=True)
        finally:
            if os.path.exists(audio_file_path):
                os.unlink(audio_file_path)
            if os.path.exists(resume_file_path):
                os.unlink(resume_file_path)

    # 3. 后台启动一个线程运行它（不阻塞当前请求）
    thread = threading.Thread(target=run_analysis)
    thread.start()
    return HttpResponse.ok(msg="正在分析中...")


@router.post("audio_2_text")
async def audio_2_text_api(audio_file: UploadFile = File(...),):
    audio_file_path = await save_upload_file_to_temp(audio_file, use_original_filename=True)
    try:
        instance = InterviewAnalysis(audio_file=audio_file_path)
        content = instance.audio_2_text_public()
    except Exception as e:
        raise e
    finally:
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)

    text_bytes = content.encode("utf-8")
    safe_filename = quote(Path(audio_file_path).stem, safe="")
    headers = {
        "Content-Disposition": f"attachment; filename=\"fallback.txt\"; filename*=UTF-8''{safe_filename}"
    }
    return Response(
        content=text_bytes,
        media_type="text/plain",
        headers=headers
    )
