import logging
import os

from Base.Service.ttsService import TtsService
from Wolin.db.commonQuestion import common_questions, normal_questions

logger = logging.getLogger(__name__)


def init_question_tts(voice: str = "中文女",questions: list[str] = common_questions):
    """
    将所有主观面试题转换为 TTS 音频并缓存到 MinIO。
    已存在的音频会自动跳过，不会重复存储。
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    tts_conf = {"bucket_name": "tts-audio-cache"}
    bucket_name = tts_conf.get("bucket_name")
    service = TtsService(voice=voice)

    total = len(questions)
    hit = 0
    uploaded = 0
    failed = 0

    logger.info(f"开始初始化面试题 TTS 缓存，共 {total} 条")

    for idx, question in enumerate(questions, 1):
        object_name = service._build_object_name(voice, question)

        # 检查 MinIO 是否已有缓存
        if service._minio_client.object_exists(service.bucket_name, object_name):
            hit += 1
            logger.info(f"[{idx}/{total}] 缓存已存在，跳过: {question[:20]}...")
            continue

        # 合成并上传
        url = service.synthesize(question, voice=voice)
        if url:
            uploaded += 1
            logger.info(f"[{idx}/{total}] 合成成功: {question[:20]}...")
        else:
            failed += 1
            logger.error(f"[{idx}/{total}] 合成失败: {question}")

    logger.info(f"初始化完成: 总计 {total}, 命中缓存 {hit}, 新上传 {uploaded}, 失败 {failed}")


if __name__ == "__main__":
    init_question_tts()
    init_question_tts(questions=normal_questions)
