from Base.Client import asr_client
from Base.RicUtils.audioFileUtils import AudioFileHandler
from Base.RicUtils.redisUtils import cache_with_params


@cache_with_params(key_template="audio_2_text_with_cache:{audio_path}{max_workers}", expire=3600)
def audio_file_2_text_with_cache(audio_path: str, max_workers: int = 50):
    """
    Redis 缓存封装版本 audio_file_2_text
    :param audio_path:
    :param max_workers:
    :return:
    """
    handler = AudioFileHandler()
    # 将文件拆成碎片
    temp_file_list = handler.split_audio_with_overlap_ffmpeg(input_audio_path=audio_path
                                                             , max_segment_duration=100
                                                             , overlap_duration=2
                                                             , output_format='wav')
    return asr_client.audio_2_text(file_path=temp_file_list,max_workers=max_workers)