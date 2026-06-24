"""
评估器基类

提供评估器抽象基类和结果对象。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel, Field

from ..base import AgentContext


class EvalResult(BaseModel):
    """评估结果"""
    evaluator_name: str
    score: float = 0.0
    dimensions: Dict[str, float] = Field(default_factory=dict)
    feedback: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseEvaluator(ABC):
    """评估器抽象基类"""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def evaluate(self, ctx: AgentContext) -> EvalResult:
        """
        执行评估

        Args:
            ctx: Agent 上下文

        Returns:
            评估结果
        """
        pass

    @abstractmethod
    def is_applicable(self, ctx: AgentContext) -> bool:
        """判断是否适用于当前请求"""
        pass
