import os

from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage
from openai import OpenAI

load_dotenv()

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)



chatLLM = ChatTongyi(
    streaming=True,
    api_key= os.getenv("DASHSCOPE_API_KEY")
)


def ez_invoke(sys_msg: str, usr_msg: str):
    """
    基于 Langchain库去调用llm
    :param sys_msg:
    :param usr_msg:
    :return:
    """
    result = chatLLM.invoke([SystemMessage(content=sys_msg), HumanMessage(content=usr_msg)])
    return result.content

def ez_llm(sys_msg: str, usr_msg: str):
    """
    基于Open-Ai库去调用llm
    :param sys_msg:
    :param usr_msg:
    :return:
    """
    # noinspection PyTypeChecker
    completion = client.chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model="qwen3-max", # qwen-plus
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": usr_msg},
        ]
    )
    return completion.choices[0].message.content

if __name__ == '__main__':
    # res = chatLLM.invoke([HumanMessage(content="hi")])
    # print(res.content)
    res = ez_llm(sys_msg="你是一个有趣的AI助理，你能帮助我完成以下任务：\n",usr_msg='你好')
    print(res)
    # res = chatLLM.stream([HumanMessage(content="1 + 1 = ?")])
    # for r in res:
    #     print("chat resp:", r)