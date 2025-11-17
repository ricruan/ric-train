import os
import dashscope



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
            messages: list):
        response = dashscope.MultiModalConversation.call(
            # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            model="qwen3-asr-flash",
            messages=messages,
            result_format="message",
            asr_options={
                "language": "zh",
                "enable_itn": True
            }
        )
        return response


# 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# 请用您的本地音频的绝对路径替换 ABSOLUTE_PATH/welcome.mp3
audio_file_path = "file://ABSOLUTE_PATH/welcome.mp3"

messages = [
    {"role": "system", "content": [{"text": ""}]},  # 配置定制化识别的 Context
    {"role": "user", "content": [{"audio": audio_file_path}]}
]
response = dashscope.MultiModalConversation.call(
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen3-asr-flash",
    messages=messages,
    result_format="message",
    asr_options={
        # "language": "zh", # 可选，若已知音频的语种，可通过该参数指定待识别语种，以提升识别准确率
        "enable_itn": True
    }
)
print(response)
