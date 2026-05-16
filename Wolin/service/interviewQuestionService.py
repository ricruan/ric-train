import hashlib
import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime
from typing import Optional

from Wolin.models.po.interviewQuestionPo import InterviewQuestionPo
from Wolin.models.po.interviewRecordPo import InterviewRecordPo
from Wolin.prompt.interviewQuestionPrompt import INTERVIEW_QUESTIONS_GENERATE_PROMPT
from Wolin.service.base import service_logger
from Base.Client.minioClient import MinioClient
from Base.Client.qwen import ez_llm
from Base.Service.ttsService import synthesize_tts

logger = service_logger


def extract_interview_questions(resume_text: str) -> list[str]:
    """
    基于简历文本，调用 LLM 生成 10 个面试问题。

    :param resume_text: 简历解析文本
    :return: 面试问题列表
    """
    response = ez_llm(INTERVIEW_QUESTIONS_GENERATE_PROMPT, resume_text)
    questions = _parse_questions(response)
    logger.info(f"从简历中生成 {len(questions)} 个面试问题")
    return questions


def _parse_questions(raw: str) -> list[str]:
    """从 LLM 返回的文本中解析出 JSON 数组。"""
    text = raw.strip()
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        text = match.group(0)

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(q).strip() for q in data if str(q).strip()]
    except json.JSONDecodeError:
        logger.error(f"LLM 返回内容无法解析为 JSON: {raw[:200]}")

    return [line.strip() for line in text.split("\n") if line.strip()]


def generate_interview_audio(resume_file_path: str, voice: str = "中文女") -> list[dict]:
    """
    传入简历文件路径，返回包含问题和对应 TTS 预签名 URL 的字典列表。

    :param resume_file_path: 简历文件路径
    :param voice: 合成音色
    :return: [{"question": "...", "audio_url": "https://..."}]
    """
    resume_text = _read_resume(resume_file_path)
    questions = extract_interview_questions(resume_text)

    results = []
    for question in questions:
        audio_url = synthesize_tts(text=question, voice=voice)
        if audio_url:
            results.append({"question": question, "audio_url": audio_url})
        else:
            logger.warning(f"TTS 合成失败，跳过问题: {question[:50]}")

    logger.info(f"成功生成 {len(results)}/{len(questions)} 个带音频的问题")
    return results


def generate_and_store_questions_async(
    resume_file_path: str,
    user_name: str,
    voice: str = "中文女",
):
    """
    后台异步执行：先生成问题并持久化，再逐个调用 TTS 合成音频并更新对应数据。

    流程：
    1. 创建 interview_records 记录（status=processing）
    2. 读取简历 → LLM 生成问题
    3. 批量写入 interview_questions 表（tts_audio_path 为空）
    4. 逐个调用 TTS 合成 → 自动上传 MinIO → 返回预签名 URL → 更新记录
    5. 更新 interview_records 状态为 completed
    """
    record_uuid = str(uuid.uuid4())

    try:
        # 1. 创建面试记录
        record = InterviewRecordPo(
            record_uuid=record_uuid,
            user_name=user_name or "匿名用户",
            status="processing",
            resume_file_path=resume_file_path,
        )
        record.save()
        logger.info(f"已创建面试记录 record_uuid={record_uuid}")

        # 2. 读取简历 → LLM 生成问题
        resume_text = _read_resume(resume_file_path)
        questions = extract_interview_questions(resume_text)

        # 3. 批量写入问题表（不含音频路径）
        question_records = [
            InterviewQuestionPo(
                record_uuid=record_uuid,
                question_text=q,
                question_order=idx,
            )
            for idx, q in enumerate(questions)
        ]

        if question_records:
            InterviewQuestionPo.bulk_insert(question_records)
            logger.info(f"已持久化 {len(question_records)} 条面试问题（无音频）")

            # 4. 逐个生成 TTS 并更新对应记录（TTS 已自动上传 MinIO 并返回预签名 URL）
            saved_questions = InterviewQuestionPo.find_by(
                record_uuid=record_uuid,
                order_by="question_order",
            )
            for idx, saved in enumerate(saved_questions):
                audio_url = synthesize_tts(text=saved.question_text, voice=voice)
                if audio_url:
                    saved.update(tts_audio_path=audio_url)
                    logger.info(f"问题 {idx + 1} TTS URL: {audio_url}")
                else:
                    logger.warning(f"TTS 合成失败，问题 {idx + 1}: {saved.question_text[:50]}")

        # 5. 更新记录状态
        record.update(status="completed", completed_at=datetime.now())
        logger.info(f"面试问题生成完成 record_uuid={record_uuid}")

    except Exception as e:
        logger.error(f"后台生成面试问题失败 record_uuid={record_uuid}: {e}", stack_info=True)
        try:
            failed_record = InterviewRecordPo.find_one_by(record_uuid=record_uuid)
            if failed_record:
                failed_record.update(
                    status="failed",
                    error_msg=str(e),
                    completed_at=datetime.now(),
                )
        except Exception:
            pass
    finally:
        if resume_file_path and os.path.exists(resume_file_path):
            os.unlink(resume_file_path)


def get_questions_with_audio_url(
    record_uuid: str,
    expiry_hours: int = 24,
    voice: str = "中文女",
) -> list[dict]:
    """
    根据 record_uuid 查询面试问题列表，返回音频访问 URL。
    URL 在每次查询时动态生成，不存在过期问题。
    若 tts_audio_path 为空，则从 question_text 重建 object_name 并尝试回补。

    :param record_uuid: 面试记录 UUID
    :param expiry_hours: 预签名 URL 有效期（小时）
    :param voice: 默认音色（用于重建缺失的 object_name）
    :return: [{"question": "...", "audio_url": "https://..."}]
    """
    saved_questions = InterviewQuestionPo.find_by(
        record_uuid=record_uuid,
        order_by="question_order",
    )

    minio_client = MinioClient() if saved_questions else None
    results = []
    for item in saved_questions:
        audio_url = None
        object_name = None

        if item.tts_audio_path:
            # 已存储 object_name，直接生成 URL
            object_name = item.tts_audio_path
        else:
            # 字段为空，从 question_text + voice 重建 object_name
            text_hash = hashlib.md5(item.question_text.encode("utf-8")).hexdigest()
            object_name = f"{voice}/{text_hash}.wav"

        if object_name and minio_client:
            audio_url = minio_client.get_presigned_url(
                "tts-audio-cache",
                object_name,
                expiry_hours=expiry_hours,
            )
            # 如果是从空字段重建的且成功生成，回写 DB
            if audio_url and not item.tts_audio_path:
                item.update(tts_audio_path=object_name)

        results.append({
            "question": item.question_text,
            "audio_url": audio_url,
        })

    return results


def _read_resume(file_path: str) -> str:
    """读取简历文件内容。"""
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext in ("txt", "md"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    if ext == "pdf":
        return _read_pdf(file_path)

    if ext in ("docx", "doc"):
        return _read_docx(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def _read_pdf(file_path: str) -> str:
    try:
        from pdfminer.high_level import extract_text
        return extract_text(file_path) or ""
    except ImportError:
        try:
            import fitz
            doc = fitz.open(file_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        except ImportError:
            logger.error("请安装 pdfminer.six 或 PyMuPDF 以支持 PDF 解析")
            return ""
    except Exception as e:
        logger.error(f"PDF 解析失败: {e}")
        return ""


def _read_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        logger.error("python-docx 未安装，请安装: pip install python-docx")
        return ""
    except Exception as e:
        logger.error(f"DOCX 解析失败: {e}")
        return ""
