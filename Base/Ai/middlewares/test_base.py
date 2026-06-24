"""中间件基类测试"""
import pytest
import asyncio
from Base.Ai.middlewares.base import AgentContext, Middleware, MiddlewareChain


class MockMiddleware(Middleware):
    """测试用中间件"""

    def __init__(self, name: str):
        self.name = name
        self.request_called = False
        self.response_called = False

    async def process_request(self, ctx: AgentContext, next):
        self.request_called = True
        ctx.metadata[f"{self.name}_request"] = True
        await next()

    async def process_response(self, ctx: AgentContext):
        self.response_called = True
        ctx.metadata[f"{self.name}_response"] = True


class TestAgentContext:
    """AgentContext 测试"""

    def test_default_values(self):
        """测试默认值"""
        ctx = AgentContext()
        assert ctx.request_id
        assert ctx.output == ""
        assert ctx.duration_ms == 0
        assert ctx.token_usage == {}
        assert ctx.tool_calls == []
        assert ctx.error is None

    def test_custom_values(self):
        """测试自定义值"""
        ctx = AgentContext(
            user_input="test input",
            agent_name="TestAgent",
        )
        assert ctx.user_input == "test input"
        assert ctx.agent_name == "TestAgent"


class TestMiddlewareChain:
    """MiddlewareChain 测试"""

    def test_use_middleware(self):
        """测试注册中间件"""
        chain = MiddlewareChain()
        mw = MockMiddleware("test")
        chain.use(mw)
        assert len(chain.middlewares) == 1

    def test_use_invalid_middleware(self):
        """测试注册无效中间件"""
        chain = MiddlewareChain()
        with pytest.raises(TypeError):
            chain.use("not a middleware")

    @pytest.mark.asyncio
    async def test_execute_chain(self):
        """测试执行中间件链"""
        chain = MiddlewareChain()
        mw1 = MockMiddleware("mw1")
        mw2 = MockMiddleware("mw2")
        chain.use(mw1)
        chain.use(mw2)

        ctx = AgentContext(user_input="test")
        handler_called = False

        async def handler(ctx):
            nonlocal handler_called
            handler_called = True
            ctx.output = "handler output"

        await chain.execute(ctx, handler)

        assert handler_called
        assert mw1.request_called
        assert mw1.response_called
        assert mw2.request_called
        assert mw2.response_called
        assert ctx.output == "handler output"
        assert ctx.metadata.get("mw1_request") is True
        assert ctx.metadata.get("mw2_request") is True
        assert ctx.metadata.get("mw1_response") is True
        assert ctx.metadata.get("mw2_response") is True
