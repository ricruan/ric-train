from enum import Enum


class LLMTypeEnum(Enum):
    """LLM类型枚举"""
    QWEN = 'qwen'
    """千问"""
    DEEPSEEK = 'deepseek'
    """深度求索"""


class AgentParadigmEnum(Enum):
    """Agent 执行范式枚举"""
    REACT = 'react'
    """ReAct: Reason + Act 循环，工具调用与推理交替"""
    COT = 'cot'
    """Chain of Thought: 逐步推理后给出答案"""
    PLAN_AND_EXECUTE = 'plan_and_execute'
    """Plan and Execute: 先规划执行计划，再逐步执行"""