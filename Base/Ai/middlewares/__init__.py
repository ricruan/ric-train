"""
Agent 中间件模块

提供可观测性、安全性、评估等中间件。
"""
from .base import AgentContext, Middleware, MiddlewareChain
from .logging import LoggingMiddleware
from .metrics import MetricsMiddleware
from .safety_middleware import SafetyMiddleware
from .eval_middleware import EvalMiddleware

# 安全防护器
from .safety import (
    SafetyGuard,
    GuardResult,
    SafetyException,
    PromptInjectionDetector,
    SensitiveWordFilter,
    PIIMasker,
    ToolGuard,
)

# 评估器
from .eval import (
    BaseEvaluator,
    EvalResult,
)
from .eval.llm_judge import LLMJudgeEvaluator
from .eval.ab_test import ABTestEvaluator

__all__ = [
    # 基类
    "AgentContext",
    "Middleware",
    "MiddlewareChain",
    # 中间件
    "LoggingMiddleware",
    "MetricsMiddleware",
    "SafetyMiddleware",
    "EvalMiddleware",
    # 安全防护
    "SafetyGuard",
    "GuardResult",
    "SafetyException",
    "PromptInjectionDetector",
    "SensitiveWordFilter",
    "PIIMasker",
    "ToolGuard",
    # 评估
    "BaseEvaluator",
    "EvalResult",
    "LLMJudgeEvaluator",
    "ABTestEvaluator",
]
