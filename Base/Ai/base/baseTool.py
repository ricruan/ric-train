"""
Agent 工具基类与装饰器

提供工具注册、OpenAI function calling schema 生成、装饰器自动注册能力。
"""
import functools
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Callable
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 全局工具注册表
_tool_registry: Dict[str, "BaseTool"] = {}


class BaseTool(ABC):
    """
    Agent 工具基类

    每个工具需要提供：名称、描述、参数 schema、执行逻辑。
    子类需实现 execute 方法。
    """

    name: str = ""
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = None

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        args_schema: Optional[Type[BaseModel]] = None,
    ):
        if name:
            self.name = name
        if description:
            self.description = description
        if args_schema:
            self.args_schema = args_schema

        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.description:
            raise ValueError(f"Tool description cannot be empty for tool '{self.name}'")

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行工具逻辑（子类必须实现）"""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """
        生成 OpenAI function calling 格式的 schema

        Returns:
            {"type": "function", "function": {"name", "description", "parameters"}}
        """
        schema: Dict[str, Any] = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
            }
        }

        if self.args_schema:
            schema["function"]["parameters"] = self.args_schema.model_json_schema()
        else:
            schema["function"]["parameters"] = {
                "type": "object",
                "properties": {},
            }

        return schema

    def run(self, **kwargs) -> Any:
        """
        执行工具（带参数校验和日志）

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        logger.debug(f"执行工具 [{self.name}], 参数: {kwargs}")

        if self.args_schema:
            validated = self.args_schema(**kwargs)
            kwargs = validated.model_dump()

        try:
            result = self.execute(**kwargs)
            logger.debug(f"工具 [{self.name}] 执行完成")
            return result
        except Exception as e:
            logger.error(f"工具 [{self.name}] 执行失败: {e}", exc_info=True)
            return f"工具执行错误: {str(e)}"

    async def arun(self, **kwargs) -> Any:
        """异步执行工具（默认同步执行，子类可重写为异步）"""
        return self.run(**kwargs)

    def register(self) -> "BaseTool":
        """注册到全局工具注册表"""
        _tool_registry[self.name] = self
        return self

    @classmethod
    def from_registry(cls, name: str) -> Optional["BaseTool"]:
        """从注册表获取工具"""
        return _tool_registry.get(name)

    @classmethod
    def clear_registry(cls):
        """清空注册表"""
        _tool_registry.clear()

    def __repr__(self):
        return f"Tool(name='{self.name}', description='{self.description[:50]}...')"


class FunctionTool(BaseTool):
    """
    函数包装工具：将普通函数包装为 BaseTool 实例

    通常通过 @tool 装饰器使用，不需要直接实例化。
    """

    def __init__(
        self,
        func: Callable,
        name: str,
        description: str,
        args_schema: Optional[Type[BaseModel]] = None,
    ):
        super().__init__(name=name, description=description, args_schema=args_schema)
        self.func = func
        functools.update_wrapper(self, func)

    def execute(self, **kwargs) -> Any:
        return self.func(**kwargs)

    async def arun(self, **kwargs) -> Any:
        """如果原函数是异步的，使用异步执行"""
        import asyncio
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return self.run(**kwargs)


def tool(
    name: str,
    description: str,
    args_schema: Optional[Type[BaseModel]] = None,
    register: bool = True,
):
    """
    工具装饰器：将函数注册为 BaseTool

    Usage:
        @tool(name="calculator", description="数学计算工具", args_schema=CalcSchema)
        def calculator(a: int, b: int) -> int:
            return a + b

    Args:
        name: 工具名称（唯一标识）
        description: 工具描述（给 LLM 看）
        args_schema: Pydantic 参数 schema
        register: 是否自动注册到全局注册表
    """
    def decorator(func: Callable) -> FunctionTool:
        tool_instance = FunctionTool(
            func=func,
            name=name,
            description=description,
            args_schema=args_schema,
        )
        if register:
            tool_instance.register()
        return tool_instance

    return decorator
