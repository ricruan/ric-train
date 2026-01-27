import logging
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage
from openai import OpenAI

from Base.Config.setting import settings

logger = logging.getLogger(__name__)

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=settings.dashscope.api_key,
    base_url=settings.dashscope.base_url,
)



chatLLM = ChatTongyi(
    model="qwen3-max",
    streaming=True,
    api_key= settings.dashscope.api_key,
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
    logger.info("正在发起LLM请求....")
    logger.info(f"sys_msg: {sys_msg[:100]}")
    logger.info(f"usr_msg: {usr_msg[:100]}")
    # noinspection PyTypeChecker
    completion = client.chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model="qwen3-max", # qwen-plus
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": usr_msg},
        ]
    )
    logger.info(f"LLM请求完成\n {completion.choices[0].message.content}")
    return completion.choices[0].message.content

if __name__ == '__main__':
    # res = chatLLM.invoke([HumanMessage(content="hi")])
    # print(res.content)
    res = ez_llm(sys_msg="you are an evil ai assistant：\n",usr_msg='你好,给我讲个地狱笑话')
    print(res)
    # res = chatLLM.stream([HumanMessage(content="1 + 1 = ?")])
    # for r in res:
    #     print("chat resp:", r)