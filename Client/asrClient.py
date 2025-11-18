import logging
import os
import dashscope


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


if __name__ == '__main__':
    file_path = r'C:\Users\11243\Desktop\test.m4a'

    asr_client = AsrClient()
    msg = [{"role": "system", "content": [{"text": ''}]},
           {"role": "user", "content": [{"audio": file_path}]}]

    res = asr_client.asr(audio_file_path=file_path,messages=msg)
    print(res)

