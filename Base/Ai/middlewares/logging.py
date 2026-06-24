"""
结构化日志中间件

使用 JSON 格式记录请求/响应日志，写入本地文件。
"""
import os
import json
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Callable, Optional

from .base import AgentContext, Middleware


class LoggingMiddleware(Middleware):
    """
    结构化日志中间件

    使用 JSON 格式记录请求/响应，便于后续分析和检索。
    """

    def __init__(
        self,
        log_dir: str = "logs/agent",
        log_level: str = "INFO",
        log_request_body: bool = True,
        log_response_body: bool = True,
        max_body_length: int = 1000,
    ):
        self.log_dir = log_dir
        self.log_level = log_level
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_length = max_body_length

        # 初始化 logger
        self._logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """配置 JSON 格式的 logger"""
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)

        logger = logging.getLogger(f"agent.trace.{id(self)}")
        logger.setLevel(getattr(logging, self.log_level.upper()))

        # 避免重复添加 handler
        if not logger.handlers:
            log_file = os.path.join(self.log_dir, "agent-trace.log")
            handler = TimedRotatingFileHandler(
                filename=log_file,
                when="midnight",
                backupCount=30,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)

        return logger

    def _truncate(self, text: Optional[str]) -> str:
        """截断文本"""
        if not text:
            return ""
        if len(text) > self.max_body_length:
            return text[: self.max_body_length] + "..."
        return text

    async def process_request(self, ctx: AgentContext, next: Callable):
        """记录请求日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "request",
            "request_id": ctx.request_id,
            "agent_name": ctx.agent_name,
            "user_input": self._truncate(ctx.user_input) if self.log_request_body else "***",
            "metadata": {
                k: v
                for k, v in ctx.metadata.items()
                if isinstance(v, (str, int, float, bool))
            },
        }
        self._logger.info(json.dumps(log_entry, ensure_ascii=False))

        await next()

    async def process_response(self, ctx: AgentContext):
        """记录响应日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "response",
            "request_id": ctx.request_id,
            "agent_name": ctx.agent_name,
            "duration_ms": ctx.duration_ms,
            "output": self._truncate(ctx.output) if self.log_response_body else "***",
            "tool_calls_count": len(ctx.tool_calls),
            "success": ctx.error is None,
            "error": str(ctx.error) if ctx.error else None,
        }
        self._logger.info(json.dumps(log_entry, ensure_ascii=False))
