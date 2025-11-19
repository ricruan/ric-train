import json
import logging
import concurrent.futures
import os
import threading
from typing import List, Tuple, Any

from Client.asrClient import AsrClient
from Client.qwen import ez_invoke, ez_llm
from RicUtils.audioFileUtils import AudioFileHandler
from RicUtils.docUtils import generate_doc_with_jinja
from Wolin.prompt.insertviewPrompt import COMBINE_SLICE, ANALYSIS_START_PROMPT, REPORT_PROMPT, CORE_QA_EXTRACT_PROMPT, \
    CORE_QA_ANALYSIS_PROMPT, render, INTERVIEW_EVALUATION_PROMPT, SELF_EVALUATION_PROMPT, ANALYSIS_END_PROMPT, test2, \
    test


class InterviewAnalysis:
    asr_client = AsrClient()
    file_handler = AudioFileHandler()


    def __init__(self):
        self.context_params = {
            "name":"沃林出品"
        }
        self.analysis_start_event = threading.Event()
        self.content = ''
        pass


    def _analysis_start(self):
        """
        分析报告第一段
        :param content:
        :return:
        """
        result = ez_llm(sys_msg=ANALYSIS_START_PROMPT,usr_msg=self.content)
        self.context_params['analysis_start'] = result
        self.analysis_start_event.set()
        return result

    def _basic_report_json(self):
        """
        报告的基础JSON
        :param content:
        :return:
        """
        result = ez_llm(sys_msg=REPORT_PROMPT, usr_msg=self.content)
        res_json = json.loads(result)
        self.context_params = {**res_json, **self.context_params}
        return result


    def _qa_analysis(self):
        """
        技术问题点评
        :param content:
        :return:
        """
        result = ez_llm(sys_msg=CORE_QA_EXTRACT_PROMPT,usr_msg=self.content)
        final_result = ez_llm(sys_msg=CORE_QA_ANALYSIS_PROMPT,usr_msg=result)
        res = json.loads(final_result)
        self.context_params['qa_analysis'] = res
        return final_result



    def _interview_evaluation(self):
        result = ez_llm(sys_msg=render(INTERVIEW_EVALUATION_PROMPT,{"analysis_start":self.context_params['analysis_start']}),usr_msg=self.content)
        self.context_params['interview_evaluation'] = result
        return result

    def _self_evaluation(self):
        result = ez_llm(sys_msg=render(SELF_EVALUATION_PROMPT, {"analysis_start": self.context_params['analysis_start']}), usr_msg=self.content)
        self.context_params['self_evaluation'] = result
        return result

    def _analysis_end(self):
        result = ez_llm(sys_msg=render(ANALYSIS_END_PROMPT, {"analysis_start": self.context_params['analysis_start']}), usr_msg=self.content)
        self.context_params['analysis_end'] = result
        return result

    def _generate_report(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, "template.docx")
        output_path = os.path.join(script_dir, "output_docxtpl.docx")
        generate_doc_with_jinja(template_path, output_path, self.context_params)


    def _task(self):
        # 可并行的任务（不依赖 analysis_start 结果）
        task1 = threading.Thread(target=self._analysis_start)
        task2 = threading.Thread(target=self._basic_report_json)
        task3 = threading.Thread(target=self._qa_analysis)

        task1.start()
        task2.start()
        task3.start()

        # 等待关键任务完成（analysis_start 设置 Event）
        self.analysis_start_event.wait()

        # 依赖 analysis_start 的任务（可串行或再开线程）
        task4 = threading.Thread(target=self._interview_evaluation)
        task5 = threading.Thread(target=self._self_evaluation)
        task6 = threading.Thread(target=self._analysis_end)

        task4.start()
        task5.start()
        task6.start()

        # 可选：等待所有线程结束
        task1.join()
        task2.join()
        task3.join()
        task4.join()
        task5.join()
        task6.join()
        task7 = threading.Thread(target=self._generate_report)
        task7.start()
        task7.join()

    def analysis(self, file_path: str):

        # temp_file_list = self.file_handler.split_audio_with_overlap_ffmpeg(input_audio_path=file_path
        #                                                                    ,max_segment_duration=100)
        # asr_res = self.audio_2_text(temp_file_list)
        # print(asr_res)
        asr_res = test
        text = self.combine_slice_by_llm(asr_res)
        self.content = text
        self._task()
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
    def combine_slice_by_llm(slice_list: list[str] | str):
        return ez_llm(sys_msg=COMBINE_SLICE,usr_msg=str(slice_list))



if __name__ == "__main__" :
    logging.basicConfig(level=logging.INFO)
    input_file = r"C:\Users\11243\Desktop\华为线下面试录音.mp3"

    ins = InterviewAnalysis()
    ins.analysis(input_file)

