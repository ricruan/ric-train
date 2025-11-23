import json
import logging
import concurrent.futures
import os
import threading
from typing import List, Tuple, Any

from Client.asrClient import AsrClient
from Client.qwen import ez_llm
from Client.redisClient import RedisClient
from RicUtils.audioFileUtils import AudioFileHandler
from RicUtils.decoratorUtils import after_exec_4c
from RicUtils.docUtils import generate_doc_with_jinja
from RicUtils.pdfUtils import extract_pdf_text
from RicUtils.redisUtils import cache_with_params
from Wolin.prompt.insertviewPrompt import COMBINE_SLICE, ANALYSIS_START_PROMPT, REPORT_PROMPT, CORE_QA_EXTRACT_PROMPT, \
    CORE_QA_ANALYSIS_PROMPT, render, INTERVIEW_EVALUATION_PROMPT, SELF_EVALUATION_PROMPT, ANALYSIS_END_PROMPT, test2, \
    test, RESUME_JSON_EXTRACT_PROMPT, RESUME_ANALYSIS_PROMPT


class InterviewAnalysis:
    asr_client = AsrClient()
    file_handler = AudioFileHandler()
    redis_client = RedisClient()

    def __init__(self):
        self.context_params = {
            "resume_info": {}
        }
        self.analysis_start_event = threading.Event()
        self.content = ''
        self.resume_file = ''
        pass

    def _analysis_start(self):
        """
        分析报告第一段
        :param content:
        :return:
        """
        result = ez_llm(sys_msg=ANALYSIS_START_PROMPT, usr_msg=self.content)
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
        result = ez_llm(sys_msg=CORE_QA_EXTRACT_PROMPT, usr_msg=self.content)
        final_result = ez_llm(sys_msg=CORE_QA_ANALYSIS_PROMPT, usr_msg=result)
        res = json.loads(final_result)
        self.context_params['qa_analysis'] = res
        return final_result

    def _interview_evaluation(self):
        result = ez_llm(
            sys_msg=render(INTERVIEW_EVALUATION_PROMPT, {"analysis_start": self.context_params['analysis_start']}),
            usr_msg=self.content)
        self.context_params['interview_evaluation'] = result
        return result

    def _self_evaluation(self):
        result = ez_llm(
            sys_msg=render(SELF_EVALUATION_PROMPT, {"analysis_start": self.context_params['analysis_start']}),
            usr_msg=self.content)
        self.context_params['self_evaluation'] = result
        return result

    def _analysis_end(self):
        result = ez_llm(sys_msg=render(ANALYSIS_END_PROMPT, {"analysis_start": self.context_params['analysis_start']}),
                        usr_msg=self.content)
        self.context_params['analysis_end'] = result
        return result

    def _generate_report(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, "template.docx")
        output_path = os.path.join(script_dir, "output_docxtpl.docx")
        print("================")
        print(self.context_params)
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
        task3_5 = threading.Thread(target=self.read_resume)
        task4 = threading.Thread(target=self._interview_evaluation)
        task5 = threading.Thread(target=self._self_evaluation)
        task6 = threading.Thread(target=self._analysis_end)

        task3_5.start()
        task4.start()
        task5.start()
        task6.start()

        # 可选：等待所有线程结束
        task1.join()
        task2.join()
        task3.join()
        task3_5.join()
        task4.join()
        task5.join()
        task6.join()
        task7 = threading.Thread(target=self._generate_report)
        task7.start()
        task7.join()

    @cache_with_params(key_template="InterviewAnalysis:split_audio:{file_path}", expire=3600)
    def _split_audio_combine_2_text(self, file_path: str):
        temp_file_list = self.file_handler.split_audio_with_overlap_ffmpeg(input_audio_path=file_path
                                                                           , max_segment_duration=100
                                                                           , output_format='wav')
        asr_res = self.audio_2_text(temp_file_list)
        text = self.combine_slice_by_llm(asr_res, self.context_params.get('resume_info'))
        return text

    def analysis(self, file_path: str):
        """"
        Interview Analysis Core Function
        :param file_path: Audio File Path
        :return:
        """
        self.read_resume(file_path=self.resume_file)
        text = self._split_audio_combine_2_text(file_path=file_path)
        self.content = text
        self._task()
        return text

    def read_resume_after(self, read_resume_result: tuple):
        self.context_params['resume_info'] = read_resume_result[0]
        self.context_params['resume_analysis'] = read_resume_result[1]

    @after_exec_4c(read_resume_after)
    @cache_with_params(key_template="InterviewAnalysis:resume_info:{file_path}", expire=3600)
    def read_resume(self, file_path: str = None):
        """
        读取简历文件
        :param file_path:
        :return:
        """
        if not file_path:
            file_path = self.resume_file
        # TODO 这里拆一下，简历分析 不要被缓存
        resume_content = extract_pdf_text(file_path)
        resume_info = ez_llm(sys_msg=RESUME_JSON_EXTRACT_PROMPT, usr_msg=resume_content)
        resume_info_json = json.loads(resume_info)
        resume_analysis = ez_llm(sys_msg=RESUME_ANALYSIS_PROMPT, usr_msg=resume_content)
        return resume_info_json, resume_analysis

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
    def combine_slice_by_llm(slice_list: list[str] | str, resume_info: dict):
        return ez_llm(sys_msg=render(COMBINE_SLICE, {"resume_info": resume_info}), usr_msg=str(slice_list))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # input_file = r"C:\Users\11243\Desktop\邱俊豪东风日产.aac"
    input_file = r'C:\Users\11243\Desktop\黄立强南方电网.m4a'
    resume_file_path = r'C:\Users\11243\Desktop\黄简历.pdf'

    ins = InterviewAnalysis()
    ins.resume_file = resume_file_path
    ins.analysis(input_file)
    # res = ins.read_resume(file_path=r"C:\Users\11243\Desktop\黄简历.pdf")
    # print(res)
