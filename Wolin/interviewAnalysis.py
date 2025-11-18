import logging
import concurrent.futures
from typing import List, Tuple, Any

from Client.asrClient import AsrClient
from Client.qwen import ez_invoke, ez_llm
from RicUtils.audioFileUtils import AudioFileHandler
from Wolin.prompt.insertviewPrompt import COMBINE_SLICE


class InterviewAnalysis:
    asr_client = AsrClient()
    file_handler = AudioFileHandler()


    def __init__(self):
        pass


    def analysis(self, file_path: str):
        temp_file_list = self.file_handler.split_audio_with_overlap_ffmpeg(input_audio_path=file_path
                                                                           ,max_segment_duration=100)
        asr_res = self.audio_2_text(temp_file_list)
        text = self.combine_slice_by_llm(asr_res)
        return text


    def audio_2_text(self, file_path: str | list[str], max_workers: int = 25):
        """
        使用线程池并发运行 ASR 函数，并保持原始顺序
        
        Args:
            file_path: 单个文件路径或文件路径列表
            max_workers: 最大并发线程数
            
        Returns:
            List[str]: 按原始顺序排列的 ASR 结果列表
        """
        if isinstance(file_path, str):
            file_path = [file_path]
        
        # 如果只有一个文件，直接处理
        if len(file_path) == 1:
            return [self.asr_client.asr(audio_file_path=file_path[0], extract_response=True)]
        
        # 创建任务列表：(索引, 文件路径)
        tasks_with_index = [(index, file) for index, file in enumerate(file_path)]
        
        def process_single_audio(task_data: Tuple[int, str]) -> Tuple[int, Any]:
            """处理单个音频文件，返回 (原始索引, ASR结果)"""
            index, audio_file = task_data
            try:
                result = self.asr_client.asr(audio_file_path=audio_file, extract_response=True)
                return index, result
            except Exception as e:
                logging.error(f"处理文件 {audio_file} 时出错: {e}")
                return index, f"处理失败: {str(e)}"
        
        # 使用线程池并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(process_single_audio, task): task[0] 
                for task in tasks_with_index
            }
            
            # 收集结果
            results_with_index = []
            for future in concurrent.futures.as_completed(future_to_index):
                try:
                    index, result = future.result()
                    results_with_index.append((index, result))
                    logging.info(f"完成处理文件索引 {index}")
                except Exception as e:
                    original_index = future_to_index[future]
                    logging.error(f"获取文件索引 {original_index} 的结果时出错: {e}")
                    results_with_index.append((original_index, f"获取结果失败: {str(e)}"))
        
        # 按原始索引排序，恢复顺序
        results_with_index.sort(key=lambda x: x[0])
        
        # 提取结果，去除索引
        ordered_results = [result for index, result in results_with_index]
        
        logging.info(f"并发处理完成，共处理 {len(ordered_results)} 个文件")
        return ordered_results


    @staticmethod
    def combine_slice_by_llm(slice_list: list[str]):
        return ez_llm(sys_msg=COMBINE_SLICE,usr_msg=str(slice_list))



if __name__ == "__main__" :
    logging.basicConfig(level=logging.INFO)
    input_file = r"C:\Users\11243\Desktop\华为线下面试录音.mp3"

    ins = InterviewAnalysis()
    ins.analysis(input_file)

