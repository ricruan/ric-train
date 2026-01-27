from Base.Ai.base.baseMessages import BaseMessages

UserMessages = BaseMessages.get_user_messages
AssistantMessages = BaseMessages.get_assistant_messages
SystemMessages = BaseMessages.get_system_messages
DeveloperMessages = BaseMessages.get_developer_messages
ToolMessages = BaseMessages.get_tool_messages
FunctionMessages = BaseMessages.get_function_messages

__all__ = ["UserMessages", "AssistantMessages", "SystemMessages", "DeveloperMessages", "ToolMessages", "FunctionMessages"]