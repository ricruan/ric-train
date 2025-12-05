import json
import logging
import concurrent.futures
import os
import tempfile
import threading
import uuid
from typing import List, Tuple, Any
from Client.asrClient import AsrClient
from Client.minioClient import MinioClient
from Client.qwen import ez_llm
from Client.redisClient import RedisClient
from RicUtils.audioFileUtils import AudioFileHandler
from RicUtils.dataUtils import short_unique_hash
from RicUtils.dateUtils import get_current_date
from RicUtils.decoratorUtils import after_exec_4c, after_exec_4c_no_params
from RicUtils.docUtils import generate_doc_with_jinja
from RicUtils.pdfUtils import extract_pdf_text
from RicUtils.redisUtils import cache_with_params
from Service.emailService import EmailService
from Wolin.prompt.insertviewPrompt import COMBINE_SLICE, ANALYSIS_START_PROMPT, REPORT_PROMPT, CORE_QA_EXTRACT_PROMPT, \
    CORE_QA_ANALYSIS_PROMPT, render, INTERVIEW_EVALUATION_PROMPT, SELF_EVALUATION_PROMPT, ANALYSIS_END_PROMPT, \
    RESUME_JSON_EXTRACT_PROMPT, RESUME_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

REDIS_PREFIX = "InterviewAnalysis"

REDIS_TEMP_REPORT_KEY = f"{REDIS_PREFIX}:temp_reports"


def init_temp_reports():
    try:
        return json.loads(RedisClient().get(REDIS_TEMP_REPORT_KEY))
    except Exception:
        return {}


class InterviewAnalysis:
    asr_client = AsrClient()
    file_handler = AudioFileHandler()
    redis_client = RedisClient()
    email_service = EmailService(receiver_emails=['2366692214@qq.com'])
    temp_reports = init_temp_reports() or {}

    def __init__(self,
                 audio_file: str,
                 resume_file: str = '',
                 receive_email: str = '',
                 user_name: str = '',
                 company_name: str = ''):
        self.audio_duration = None # 音频时长
        self.context_params = {    # 模板上下文
            "resume_info": {       # 简历信息
                "name": user_name  # 用户姓名
            }
        }
        self.company_name = company_name # 面试公司
        self.analysis_start_event = threading.Event() # 工作流event
        self.content = ''    # asr 文本内容
        self.resume_file = resume_file # 简历文件路径
        self.audio_file = audio_file # 音频文件路径
        self.origin_resume_file = resume_file # 原始简历文件路径
        self.origin_audio_file = audio_file # 原始音频文件路径
        self.report_path = '' # 报告路径
        self.uuid = uuid.uuid4().hex # 唯一标识
        self.user_email = ['2366692214@qq.com'] # 报告接收邮箱
        if receive_email:
            self.user_email.append(receive_email)

    @property
    def get_username(self, nvl_name: str = ''):
        return self.context_params.get('resume_info').get('name',nvl_name)


    @staticmethod
    def clear_temp_report():
        reports = json.loads(InterviewAnalysis.temp_reports.replace("'", '"'))
        for key, value in reports.items():
            try:
                os.unlink(value)
            except FileNotFoundError:
                continue
        InterviewAnalysis.redis_client.set(REDIS_TEMP_REPORT_KEY, str({}))

    def _update_redis_temp_report(self):
        InterviewAnalysis.redis_client.set(REDIS_TEMP_REPORT_KEY, str(self.temp_reports))

    def _analysis_start(self):
        """
        分析报告第一段
        :return:
        """
        result = ez_llm(sys_msg=ANALYSIS_START_PROMPT, usr_msg=self.content)
        self.context_params['analysis_start'] = result
        self.analysis_start_event.set()
        return result

    def _basic_report_json(self):
        """
        报告的基础JSON
        :return:
        """
        result = ez_llm(sys_msg=REPORT_PROMPT, usr_msg=self.content)
        res_json = json.loads(result)
        self.context_params = {**res_json, **self.context_params}
        return result

    def _qa_analysis(self):
        """
        技术问题点评
        :return:
        """
        result = ez_llm(sys_msg=CORE_QA_EXTRACT_PROMPT, usr_msg=self.content)
        final_result = ez_llm(sys_msg=CORE_QA_ANALYSIS_PROMPT, usr_msg=result)
        res = json.loads(final_result)
        self.context_params['qa_analysis'] = res
        return final_result

    def _interview_evaluation(self):
        """
        AI代入面试官评价
        :return:
        """
        result = ez_llm(
            sys_msg=render(INTERVIEW_EVALUATION_PROMPT, {"analysis_start": self.context_params['analysis_start']}),
            usr_msg=self.content)
        self.context_params['interview_evaluation'] = result
        return result

    def _self_evaluation(self):
        """
        AI代入求职者评价
        :return:
        """
        result = ez_llm(
            sys_msg=render(SELF_EVALUATION_PROMPT, {"analysis_start": self.context_params['analysis_start']}),
            usr_msg=self.content)
        self.context_params['self_evaluation'] = result
        return result

    def _analysis_end(self):
        """
        分析报告最后一段
        :return:
        """
        result = ez_llm(sys_msg=render(ANALYSIS_END_PROMPT, {"analysis_start": self.context_params['analysis_start']}),
                        usr_msg=self.content)
        self.context_params['analysis_end'] = result
        return result

    def _send_email(self):
        """
        发送邮件
        :return:
        """
        name = self.get_username or '小伙伴'
        content = \
        f"""
        <html>
        <body>
            <p><img src="cid:wolin" ></p>
            <h1>{name},你好！</h1>
            <p>这是一封由<b>沃林数智</b>发送的面试报告邮件（ID：{self.uuid}）,请查收附件.</p>
            <p>祝你今天愉快！</p>
        </body>
        </html>
        """

        try:
            InterviewAnalysis.email_service.send_emails_ric(
                subject=f"面试报告 {get_current_date()}",
                email_content=content,
                receiver_emails=self.user_email,
                is_html=True,
                attachments=self.report_path,
                inline_images=[("Wolin/static/wolin.jpg", "wolin")]
            )
            logger.info(f"邮件发送成功！ Receives_Email:{self.user_email}")
        except Exception as e:
            logger.error(f"邮件发送异常:{e}")


    @after_exec_4c_no_params(_update_redis_temp_report)
    @after_exec_4c_no_params(_send_email)
    def _generate_report(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, "template.docx")
        logger.debug("======报告上下文参数==========")
        logger.debug(f'报告的参数上下文dict: {self.context_params}')

        output_path = generate_doc_with_jinja(template_path, self.context_params)
        logger.info(f"面试报告临时存储位置：\n {output_path}")
        InterviewAnalysis.temp_reports[self.uuid] = output_path
        MinioClient().upload_file(bucket_name="interview-report",
                                  object_name=f'{self.get_username}/{self.company_name or get_current_date()}.docx',
                                  file_path=output_path)
        if output_path:
            self.report_path = output_path
        return output_path

    def _work_flow(self):
        """
        工作流
        :return:
        """
        # 可并行的任务（不依赖 analysis_start 结果）
        task1 = threading.Thread(target=self._analysis_start)
        task2 = threading.Thread(target=self._basic_report_json)
        task3 = threading.Thread(target=self._qa_analysis)
        task3_1 = threading.Thread(target=self._resume_analysis())

        task1.start()
        task2.start()
        task3.start()
        task3_1.start()

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
        task3_1.join()
        task4.join()
        task5.join()
        task6.join()


    def _get_audio_handle_cache_key(self, file_path: str):
        """
        redis key = user_name + audio_duration + file_path
         => hash str
        :param file_path:
        :return:
        """
        if not self.audio_duration:
            self.audio_duration = AudioFileHandler.get_audio_duration(file_path)
        new_key = self.get_username + str(self.audio_duration) + file_path
        redis_key = REDIS_PREFIX + short_unique_hash(new_key)
        return redis_key

    def _get_audio_handle_cache(self, file_path: str):
        """
        redis cache 4 audio_asr_handle
        :param file_path:
        :return:
        """
        result = InterviewAnalysis.redis_client.get(self._get_audio_handle_cache_key(file_path))
        return result


    def _split_audio_combine_2_text(self, file_path: str):
        """
        对音频文件进行切片,ASR转化为文本，并合并切片文本
        With Cache of Redis
        :param file_path: 音频文件路径
        :return: 合并后文本
        """
        result = self._get_audio_handle_cache(file_path)
        if result:
            logger.info("Cache was used during audio processing.")
            return result
        temp_file_list = self.file_handler.split_audio_with_overlap_ffmpeg(input_audio_path=file_path
                                                                           , max_segment_duration=100
                                                                           , overlap_duration=2
                                                                           , output_format='wav')
        asr_res = self.audio_2_text(temp_file_list)
        # 感觉LLM拼之后丢了一些信息，打印查看下
        try:
            for i in asr_res:
                logger.info(i)
        except Exception:
            pass
        text = self.combine_slice_by_llm(asr_res, self.context_params.get('resume_info'))
        InterviewAnalysis.redis_client.set(self._get_audio_handle_cache_key(file_path), text, ex=3600)
        return text

    def analysis(self, file_path: str = None):
        """"
        Interview Analysis Core Function
        instance should be having two params : audio_file (optional if this func had file_path param) and resume_file
        :param file_path: Audio File Path
        :return:
        """
        if not (file_path or self.audio_file):
            raise Exception("audio_file or file_path is required")
        if self.resume_file:
            self.read_resume(file_path=self.resume_file)
        self.content = self._split_audio_combine_2_text(file_path=file_path or self.origin_audio_file)
        self._work_flow()
        self._generate_report()
        return self.content


    def audio_2_text_public(self, file_path: str = None):
        self.content = self._split_audio_combine_2_text(file_path=file_path or self.origin_audio_file)
        return self.content

    def read_resume_after(self, read_resume_result):
        self.context_params['resume_info'] = read_resume_result

    @after_exec_4c(read_resume_after)
    @cache_with_params(key_template="InterviewAnalysis:resume_info:{file_path}", expire=3600)
    def read_resume(self, file_path: str = None):
        """
        读取简历文件
        :param file_path:
        :return:
        """
        if not (file_path or self.resume_file):
            logger.warning("Warning when read_resume: file_path and self.resume_file both are empty!")
        resume_content = extract_pdf_text(file_path)
        resume_info = ez_llm(sys_msg=RESUME_JSON_EXTRACT_PROMPT, usr_msg=resume_content)
        resume_info_json = json.loads(resume_info)
        return resume_info_json

    def _resume_analysis(self):
        if not self.context_params.get('resume_info'):
            return
        resume_analysis = ez_llm(sys_msg=RESUME_ANALYSIS_PROMPT, usr_msg=str(self.context_params['resume_info']))
        self.context_params['resume_analysis'] = resume_analysis

    def audio_2_text(self, file_path: str | list[str], max_workers: int = 50):
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
                asr_result = self.asr_client.asr(audio_file_path=audio_file, extract_response=True)
                return index, asr_result
            except Exception as asr_error:
                logging.error(f"处理文件 {audio_file} 时出错: {asr_error}")
                return index, f"处理失败: {str(asr_error)}"

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

        temp_file_path = ''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',delete=False, encoding='utf-8') as tmp_file:
            # 写入每行（添加换行符）
            for line in ordered_results:
                tmp_file.write(line + '\n')

            # 刷新确保内容写入磁盘（某些场景需要）
            tmp_file.flush()
            temp_file_path = tmp_file.name

        MinioClient().upload_file(bucket_name="audio-text",
                                  object_name=f'{self.get_username}/{self.company_name or get_current_date()}.txt',
                                  file_path=temp_file_path)

        os.unlink(temp_file_path)

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
    # InterviewAnalysis.clear_temp_report()
    # print(init_temp_reports())
    ins = InterviewAnalysis(audio_file=input_file,resume_file=resume_file_path)
    ins.analysis()
    # res = ins.read_resume(file_path=r'C:\Users\11243\Desktop\黄简历.pdf')
    # print(res)
