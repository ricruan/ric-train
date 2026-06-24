"""
安全防护基类

提供安全防护器抽象基类和结果对象。
"""
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from ..base import AgentContext


class GuardResult(BaseModel):
    """防护检查结果"""

    passed: bool = True
    reason: str = ""
    masked_content: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical


class SafetyGuard(ABC):
    """安全防护器抽象基类"""

    name: str = ""

    @abstractmethod
    async def check(self, content: str, ctx: AgentContext) -> GuardResult:
        """
        检查内容

        Args:
            content: 待检查内容
            ctx: Agent 上下文

        Returns:
            检查结果
        """
        pass


class SafetyException(Exception):
    """安全防护异常"""

    def __init__(self, reason: str, risk_level: str = "high"):
        self.reason = reason
        self.risk_level = risk_level
        super().__init__(f"[{risk_level}] {reason}")
