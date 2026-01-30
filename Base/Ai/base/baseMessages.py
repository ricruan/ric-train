from typing import Any

from openai.types.chat import ChatCompletionUserMessageParam, ChatCompletionMessageParam, \
    ChatCompletionAssistantMessageParam, ChatCompletionSystemMessageParam, ChatCompletionDeveloperMessageParam, \
    ChatCompletionToolMessageParam, ChatCompletionFunctionMessageParam


class BaseMessages:
    """
    消息基类(封装OpenAi的消息类型 原类型名太长，不够优雅)
    """

    @staticmethod
    def get_user_messages(prompt: Any, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionUserMessageParam(content=str(prompt), role="user", name=name)

    @staticmethod
    def get_assistant_messages(prompt: Any, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionAssistantMessageParam(content=str(prompt), role="assistant", name=name)

    @staticmethod
    def get_system_messages(prompt: Any, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionSystemMessageParam(content=str(prompt), role="system", name=name)

    @staticmethod
    def get_developer_messages(prompt: Any, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionDeveloperMessageParam(content=str(prompt), role="developer", name=name)

    @staticmethod
    def get_tool_messages(prompt: Any, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionToolMessageParam(content=str(prompt), role="tool", name=name)

    @staticmethod
    def get_function_messages(prompt: Any, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionFunctionMessageParam(content=str(prompt), role="function", name=name)