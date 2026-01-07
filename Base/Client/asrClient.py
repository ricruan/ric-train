import logging
import os
import dashscope
from typing import Tuple, Any
import concurrent.futures

logger = logging.getLogger(__name__)

class AsrClient:

    def __init__(self):
        self.ds_api_url = os.getenv('DSC_API_URL', 'https://dashscope.aliyuncs.com/api/v1')

    @staticmethod
    def _get_usr_msg(audio_file_path: str):
        return {"role": "user", "content": [{"audio": audio_file_path}]}

    @staticmethod
    def _get_sys_msg(content: str):
        return {"role": "system", "content": [{"text": content}]}

    @staticmethod
    def _ez_msg(audio_file_path: str, content: str):
        return [AsrClient._get_sys_msg(content), AsrClient._get_usr_msg(audio_file_path)]

    def asr(self,
            audio_file_path: str,
            content: str = '',
            messages = None,
            extract_response: bool = False):
        """
        Asr 语音识别
        :param audio_file_path:  音频文件路径
        :param content:  System prompt content
        :param messages:  if messages, audio_file_path and content will be invalid
        :param extract_response: is need parse response?
        :return: maybe response instance or  str (audio text)
        """
        logger.info("正在发起ASR请求....")
        response = dashscope.MultiModalConversation.call(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            model="qwen3-asr-flash",
            messages= messages or self._ez_msg(audio_file_path, content),
            result_format="message",
            asr_options={
                "language": "zh",
                "enable_itn": True
            }
        )
        if extract_response:
            return self.get_content_from_response(response)
        return response

    @staticmethod
    def get_content_from_response(response):
        try:
            return '\n'.join(item['text'] for item in response.output.choices[0].message.content)
        except Exception as e:
            logger.error(f"从响应中获取内容失败：{e}")
            return response


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
            return [self.asr(audio_file_path=file_path[0], extract_response=True)]

        # 创建任务列表：(索引, 文件路径)
        tasks_with_index = [(index, file) for index, file in enumerate(file_path)]

        def process_single_audio(task_data: Tuple[int, str]) -> Tuple[int, Any]:
            """处理单个音频文件，返回 (原始索引, ASR结果)"""
            index, audio_file = task_data
            try:
                asr_result = self.asr(audio_file_path=audio_file, extract_response=True)
                return index, asr_result
            except Exception as asr_error:
                logger.error(f"处理文件 {audio_file} 时出错: {asr_error}")
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
                    logger.info(f"完成处理文件索引 {index}")
                except Exception as e:
                    original_index = future_to_index[future]
                    logger.error(f"获取文件索引 {original_index} 的结果时出错: {e}")
                    results_with_index.append((original_index, f"获取结果失败: {str(e)}"))

        # 按原始索引排序，恢复顺序
        results_with_index.sort(key=lambda x: x[0])

        # 提取结果，去除索引
        ordered_results = [result for index, result in results_with_index]

        logger.info(f"并发处理完成，共处理 {len(ordered_results)} 个文件")
        return ordered_results

asr_client = AsrClient()

if __name__ == '__main__':
    _file_path = r'C:\Users\11243\Desktop\test.m4a'


    msg = [{"role": "system", "content": [{"text": ''}]},
           {"role": "user", "content": [{"audio": _file_path}]}]

    res = asr_client.asr(audio_file_path=_file_path,messages=msg)
    print(res)

