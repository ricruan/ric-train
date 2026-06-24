"""BaseAgent 中间件集成测试"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from Base.Ai.base.baseAgent import BaseAgent, AgentResult
from Base.Ai.base.baseLlm import BaseLlm
from Base.Ai.middlewares.base import Middleware, AgentContext


class MockLLM(BaseLlm):
    """测试用 LLM"""

    def __init__(self):
        super().__init__(model_name="test-model")
        self.model_client = MagicMock()
        self.async_model_client = MagicMock()

    def init_model(self):
        pass

    @property
    def supports_streaming(self):
        return False

    @property
    def supports_embedding(self):
        return False

    @property
    def supports_asr(self):
        return False

    @property
    def supports_ocr(self):
        return False

    def _ocr(self, img_file_path, prompt, **kwargs):
        pass

    def _asr(self, audio_file_path, **kwargs):
        pass

    def _embedding(self, text, **kwargs):
        pass

    @property
    def context_window(self):
        return 4096


class TestAgent(BaseAgent):
    """测试用 Agent"""
    pass


class TrackingMiddleware(Middleware):
    """跟踪中间件"""

    def __init__(self, name: str):
        self.name = name
        self.calls = []

    async def process_request(self, ctx: AgentContext, next):
        self.calls.append(f"{self.name}_request")
        await next()

    async def process_response(self, ctx: AgentContext):
        self.calls.append(f"{self.name}_response")


class TestBaseAgentMiddlewareIntegration:
    """BaseAgent 中间件集成测试"""

    def test_agent_has_middleware_chain(self):
        """测试 Agent 有中间件链"""
        agent = TestAgent(llm=MockLLM(), name="TestAgent")
        assert hasattr(agent, "_middleware_chain")

    def test_agent_use_middleware(self):
        """测试 Agent 注册中间件"""
        agent = TestAgent(llm=MockLLM(), name="TestAgent")
        mw = TrackingMiddleware("test")
        agent.use(mw)
        assert len(agent._middleware_chain.middlewares) == 1

    def test_agent_without_middleware(self):
        """测试无中间件时走原有逻辑"""
        agent = TestAgent(llm=MockLLM(), name="TestAgent")
        # 不注册中间件，应该走原有逻辑
        result = agent.run("test input")
        assert isinstance(result, AgentResult)
