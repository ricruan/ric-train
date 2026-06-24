"""
工具防护器

提供工具调用权限控制和危险操作拦截。
"""
import re
import json
import logging
from typing import List, Optional, Set

from .base import GuardResult, SafetyGuard
from ..base import AgentContext

logger = logging.getLogger(__name__)


class ToolGuard(SafetyGuard):
    """
    工具调用防护器

    校验工具参数，拦截危险操作。
    """

    name = "tool_guard"

    # 危险操作关键词
    DANGEROUS_OPERATIONS = [
        "drop",
        "delete",
        "truncate",
        "destroy",
        "rm -rf",
        "format",
        "shutdown",
        "reboot",
        "drop table",
        "delete from",
    ]

    def __init__(
        self,
        allowed_tools: List[str] = None,
        blocked_tools: List[str] = None,
        max_argument_length: int = 10000,
    ):
        self.allowed_tools: Optional[Set[str]] = (
            set(allowed_tools) if allowed_tools else None
        )
        self.blocked_tools: Set[str] = set(blocked_tools or [])
        self.max_argument_length = max_argument_length

    async def check(self, content: str, ctx: AgentContext) -> GuardResult:
        """检查工具调用"""
        try:
            tool_call = json.loads(content) if isinstance(content, str) else content
        except json.JSONDecodeError:
            return GuardResult(passed=True)

        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("arguments", {})

        # 1. 白名单检查
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return GuardResult(
                passed=False,
                reason=f"工具 {tool_name} 不在白名单中",
                risk_level="high",
            )

        # 2. 黑名单检查
        if tool_name in self.blocked_tools:
            return GuardResult(
                passed=False,
                reason=f"工具 {tool_name} 已被禁用",
                risk_level="high",
            )

        # 3. 参数长度检查
        args_str = json.dumps(tool_args, ensure_ascii=False)
        if len(args_str) > self.max_argument_length:
            return GuardResult(
                passed=False,
                reason=f"参数长度 {len(args_str)} 超过限制 {self.max_argument_length}",
                risk_level="medium",
            )

        # 4. 危险操作检查
        for op in self.DANGEROUS_OPERATIONS:
            if op.lower() in args_str.lower():
                return GuardResult(
                    passed=False,
                    reason=f"检测到危险操作: {op}",
                    risk_level="critical",
                )

        return GuardResult(passed=True)
