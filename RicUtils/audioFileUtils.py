import logging
import os
import subprocess
import tempfile
import uuid
from RicUtils.decoratorUtils import  after_exec_4c, params_handle_4c

logger = logging.getLogger(__name__)
FFMPEG_PATH = rf"{os.getenv('FFMPEG_PATH')}"


class AudioFileHandler:

    def __init__(self):
        self.pending_files = []
        self.max_segment_duration = 1500
        self.overlap_duration = self.max_segment_duration / 10

    def __del__(self):
        self._clear_pending_files()

    def _clear_pending_files(self):
        if not self.pending_files:
            return
        cnt = 0
        for file in self.pending_files:
            try:
                if os.path.isfile(file):
                    os.remove(file)
                    cnt += 1
            except Exception as e:
                logger.error(f"临时文件({file})删除失败：{e}")
                continue
        logger.info(f"删除{cnt}个临时文件")

    @staticmethod
    def _get_ffmpeg_run_path(command: str):
        """
        获取 ffmpeg 运行路径
        期望同时适配 windows 运行环境和 Linux 运行环境
        :param command:
        :return:
        """
        return rf'{FFMPEG_PATH}\{command}.exe' if FFMPEG_PATH else command

    def _append_to_pending_list(self, file):
        self.pending_files.extend(file)

    def _split_audio_params_pre_handle(self, params):
        if not params.get('max_segment_duration'):
            params['max_segment_duration'] = self.max_segment_duration
        else:
            self.max_segment_duration = params.get('max_segment_duration')
        if not params.get('overlap_duration'):
            params['overlap_duration'] = self.max_segment_duration / 10
        if not params.get('output_dir'):
            params['output_dir'] = tempfile.gettempdir()
        if not params.get('output_format'):
            params['output_format'] = os.path.splitext(params.get('input_audio_path'))[-1].lstrip(".")
        return params

    @staticmethod
    def get_audio_duration(input_audio_path: str) -> float:
        """
        获取音频时长
        :param input_audio_path: 音频文件路径
        :return: 音频时长（秒）
        """
        try:
            result = subprocess.run([
                AudioFileHandler._get_ffmpeg_run_path('ffprobe'), '-v', 'error', '-show_entries',
                'format=duration', '-of',
                'default=noprint_wrappers=1:nokey=1', input_audio_path
            ], capture_output=True, text=True, check=True)
            duration_sec = float(result.stdout.strip())
            return duration_sec
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.info(f"❌ 无法获取音频时长: {e}")
            return 0

    @staticmethod
    def slice_audio_with_ffmpeg(
            input_audio_path: str,
            output_filename: str,
            start_time: float,
            duration: float):
        """
        使用 ffmpeg 切割音频
        :param input_audio_path: 输入音频文件路径
        :param output_filename: 输出目录
        :param start_time: 起始时间（秒）
        :param duration: 持续时间（秒）
        :return: 切割后的音频文件路径
        """
        try:
            subprocess.run([
                AudioFileHandler._get_ffmpeg_run_path('ffmpeg'), '-i', input_audio_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c', 'copy',  # 直接复制流，不重新编码
                '-y',  # 覆盖输出文件
                output_filename
            ], check=True)
            logger.info(f"✅ 已保存：{output_filename}")
            return output_filename
        except subprocess.CalledProcessError as e:
            logger.info(f"❌ 切割失败：{e}")
            return None

    @staticmethod
    def sample_fmt(input_audio_path: str, output_filename: str = None, sample_rate: int = 16000, sample_fmt: str = "s16"):
        """
        将任意音频转换为16kHz、16-bit、单声道WAV文件
        :param input_audio_path:
        :param output_filename:
        :param sample_rate: 设置采样率为16000Hz (16kHz)
        :param sample_fmt:设置采样格式为16-bit signed integer PCM
        :return:
        """
        try:
            if not output_filename:
                output_filename = os.path.join(os.path.dirname(input_audio_path), f"{os.path.basename(input_audio_path).split('.')[0]}_16k.wav")
            subprocess.run([
                AudioFileHandler._get_ffmpeg_run_path('ffmpeg'), '-i', input_audio_path,
                '-ar', str(sample_rate),
                '-ac', '1',
                '-acodec', 'pcm_s16le',
                '-y',  # 覆盖输出文件
                output_filename
            ], check=True)
            logger.info(f"✅ 已保存：{output_filename}")
            return output_filename
        except subprocess.CalledProcessError as e:
            logger.info(f"❌ 格式转换失败：{e}")
            return None

    @params_handle_4c(_split_audio_params_pre_handle)
    @after_exec_4c(_append_to_pending_list)
    def split_audio_with_overlap_ffmpeg(
            self,
            input_audio_path,
            output_dir=None,
            max_segment_duration=None,  # 20分钟，单位秒
            overlap_duration=None,  # 1分钟重叠，单位秒
            output_format=None  # 输出格式，如 "m4a", "mp3"
    ) -> list[str] | None:
        """
        使用 ffmpeg 将音频文件切割为多个小段，带有重叠

        Args:
            input_audio_path (str): 输入的音频文件路径
            output_dir (str): 切割后音频保存的目录
            max_segment_duration (int): 每段最大时长（秒）
            overlap_duration (int): 每段之间重叠的秒数
            output_format (str): 输出音频格式
        Return:
            list[str]: 切割后切块文件路径列表， 如果为空则代表未切割
        """
        # 格式转换为16kHz、16-bit、单声道WAV文件
        if output_format == "wav":
            input_audio_path = self.sample_fmt(input_audio_path)
        # 获取音频时长
        duration_sec = AudioFileHandler.get_audio_duration(input_audio_path=input_audio_path)
        logger.info(f"音频总时长：{duration_sec:.2f} 秒")

        segments = []
        current_start = 0.0
        segment_index = 1

        if duration_sec < max_segment_duration:
            logger.info(f"音频时长小于最大分段时长，不进行切割")
            return [input_audio_path]

        while current_start < duration_sec:
            # 当前段的结束时间
            current_end = current_start + max_segment_duration

            # 不能超过音频总长度
            if current_end > duration_sec:
                current_end = duration_sec

            # 实际起始时间（考虑重叠）
            actual_start = max(0, current_start)
            actual_end = min(current_end, duration_sec)

            # 段时长
            segment_duration = actual_end - actual_start

            logger.info(
                f"[分段 {segment_index}] 从 {actual_start:.2f}s 到 {actual_end:.2f}s （时长：{segment_duration:.2f}s）")

            # 输出文件名
            output_filename = os.path.join(
                output_dir, f"audio_seg{segment_index:03d}_{uuid.uuid4().hex}.{output_format}"
            )

            # 使用 ffmpeg 切割音频
            try:
                AudioFileHandler.slice_audio_with_ffmpeg(
                    input_audio_path=input_audio_path,
                    output_filename=output_filename,
                    start_time=actual_start,
                    duration=segment_duration
                )
                segments.append(output_filename)
            except subprocess.CalledProcessError as e:
                logger.info(f"❌ 切割失败：{e}")
                break

            if duration_sec == current_end:
                break
            # 更新下一段起始位置
            current_start = actual_end - overlap_duration

            if current_start < 0:
                logger.info(f"current_start重新计算结果为负数,结束切割")
                break

            segment_index += 1

        logger.info(f"\n🎉 全部切割完成，共生成 {segment_index} 个音频片段，保存在目录：{output_dir}")
        return segments


# =============================
# 使用示例
# =============================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 检查 ffmpeg 是否可用

    # 音频文件路径
    input_file = r"C:\Users\11243\Desktop\华为线下面试录音.mp3"

    # 切割后的音频保存目录
    output_folder = "split_audio_output"

    temp_dir = tempfile.gettempdir()
    # duration1 = get_audio_duration(input_audio_path=input_file)
    # print(duration1)
    # 调用函数切割音频
    handler = AudioFileHandler()
    # 格式转换
    # handler.sample_fmt(input_audio_path=input_file)

    paths = handler.split_audio_with_overlap_ffmpeg(
        input_audio_path=input_file,
    )
    print(paths)
