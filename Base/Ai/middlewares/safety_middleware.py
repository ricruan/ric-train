"""
安全中间件

组合输入/输出/工具防护器，提供完整的安全防护。
"""
import json
import asyncio
import logging
from typing import Callable, List

from .base import AgentContext, Middleware
from .safety.base import GuardResult, SafetyException, SafetyGuard
from .safety.input_guards import PromptInjectionDetector, SensitiveWordFilter
from .safety.output_guards import PIIMasker
from .safety.tool_guards import ToolGuard

logger = logging.getLogger(__name__)


class SafetyMiddleware(Middleware):
    """
    安全中间件

    组合输入/输出/工具防护器，提供完整的安全防护。
    """

    def __init__(
        self,
        input_guards: List[SafetyGuard] = None,
        output_guards: List[SafetyGuard] = None,
        tool_guards: List[SafetyGuard] = None,
        log_violations: bool = True,
    ):
        self.input_guards = input_guards or [
            PromptInjectionDetector(),
            SensitiveWordFilter(),
        ]
        self.output_guards = output_guards or [
            PIIMasker(),
        ]
        self.tool_guards = tool_guards or [
            ToolGuard(),
        ]
        self.log_violations = log_violations

    async def process_request(self, ctx: AgentContext, next: Callable):
        """输入阶段安全检查"""
        content = ctx.user_input

        for guard in self.input_guards:
            result = await guard.check(content, ctx)

            if not result.passed:
                if self.log_violations:
                    self._log_violation(guard.name, result, ctx)
                raise SafetyException(result.reason, result.risk_level)

            # 应用脱敏后的内容
            if result.masked_content:
                content = result.masked_content
                ctx.user_input = content

        await next()

    async def process_response(self, ctx: AgentContext):
        """输出阶段安全检查"""
        if not ctx.output:
            return

        content = ctx.output

        for guard in self.output_guards:
            result = await guard.check(content, ctx)

            if not result.passed:
                if self.log_violations:
                    self._log_violation(guard.name, result, ctx)
                ctx.metadata["output_violation"] = result.reason

            # 应用脱敏后的内容
            if result.masked_content:
                content = result.masked_content

        ctx.output = content

    async def check_tool_call(self, tool_call: dict, ctx: AgentContext) -> bool:
        """
        检查工具调用

        Returns:
            True: 允许执行
            Raises SafetyException: 拦截执行
        """
        for guard in self.tool_guards:
            result = await guard.check(json.dumps(tool_call), ctx)
            if not result.passed:
                if self.log_violations:
                    self._log_violation(guard.name, result, ctx)
                raise SafetyException(result.reason, result.risk_level)
        return True

    def _log_violation(
        self,
        guard_name: str,
        result: GuardResult,
        ctx: AgentContext,
    ):
        """记录安全违规"""
        logger.warning(
            f"安全违规 | Guard: {guard_name} | "
            f"Risk: {result.risk_level} | "
            f"Reason: {result.reason} | "
            f"RequestID: {ctx.request_id}"
        )
