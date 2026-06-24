"""
中间件基类与上下文

提供中间件抽象、上下文对象、中间件链执行器。
"""
import uuid
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentContext(BaseModel):
    """中间件共享的上下文对象"""

    model_config = {"arbitrary_types_allowed": True}

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_input: str = ""
    agent_name: str = ""
    start_time: float = Field(default_factory=time.time)
    output: str = ""
    duration_ms: int = 0
    token_usage: Dict[str, int] = Field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Exception] = None


class Middleware(ABC):
    """中间件抽象基类"""

    @abstractmethod
    async def process_request(
        self,
        ctx: AgentContext,
        next: Callable
    ) -> None:
        """
        处理请求(进入时)

        Args:
            ctx: 上下文对象
            next: 下一个中间件
        """
        pass

    @abstractmethod
    async def process_response(
        self,
        ctx: AgentContext
    ) -> None:
        """
        处理响应(返回时)

        Args:
            ctx: 上下文对象
        """
        pass


class MiddlewareChain:
    """
    中间件链管理器

    采用洋葱模型:先进入的中间件,后处理响应
    """

    def __init__(self):
        self._middlewares: List[Middleware] = []

    def use(self, middleware: Middleware):
        """注册中间件"""
        if not isinstance(middleware, Middleware):
            raise TypeError(f"middleware 必须是 Middleware 实例,而非 {type(middleware)}")
        self._middlewares.append(middleware)

    @property
    def middlewares(self) -> List[Middleware]:
        """获取中间件列表"""
        return self._middlewares

    async def execute(
        self,
        ctx: AgentContext,
        handler: Callable
    ) -> AgentContext:
        """
        执行中间件链

        Args:
            ctx: 上下文对象
            handler: 核心处理逻辑
        """
        index = 0
        response_indices = []

        async def next():
            nonlocal index
            if index < len(self._middlewares):
                middleware = self._middlewares[index]
                index += 1
                response_indices.append(index - 1)
                await middleware.process_request(ctx, next)
            else:
                # 到达核心逻辑
                await handler(ctx)

            # 逆向执行响应处理
            if response_indices:
                resp_idx = response_indices.pop()
                middleware = self._middlewares[resp_idx]
                await middleware.process_response(ctx)

        await next()
        return ctx
