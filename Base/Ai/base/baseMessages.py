from openai.types.chat import ChatCompletionUserMessageParam, ChatCompletionMessageParam



class BaseMessages:
    """
    消息基类(封装OpenAi的消息类型 原类型名太长，不够优雅)
    """

    @staticmethod
    def get_user_messages(prompt: str, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionMessageParam(content=prompt, role="user", name=name)

    @staticmethod
    def get_assistant_messages(prompt: str, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionMessageParam(content=prompt, role="assistant", name=name)

    @staticmethod
    def get_system_messages(prompt: str, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionMessageParam(content=prompt, role="system", name=name)

    @staticmethod
    def get_developer_messages(prompt: str, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionMessageParam(content=prompt, role="developer", name=name)

    @staticmethod
    def get_tool_messages(prompt: str, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionMessageParam(content=prompt, role="tool", name=name)

    @staticmethod
    def get_function_messages(prompt: str, name: str = None) -> ChatCompletionMessageParam:
        return ChatCompletionMessageParam(content=prompt, role="function", name=name)