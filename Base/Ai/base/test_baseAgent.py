"""
BaseAgent 测试脚本

验证：工具注册、ReAct/CoT/PlanAndExecute 范式、记忆管理。
"""
import json
import logging
from pydantic import BaseModel

from Base.Ai.base.baseTool import BaseTool, tool
from Base.Ai.base.baseAgent import (
    BaseAgent, ReActAgent, CoTAgent, PlanAndExecuteAgent,
    InMemoryMemory, AgentResult,
)
from Base.Ai.base.baseEnum import AgentParadigmEnum
from Base.Ai.llms.qwenLlm import get_default_qwen_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========== 1. 定义测试工具 ==========

class CalculatorSchema(BaseModel):
    """数学计算参数"""
    expression: str


@tool(name="calculator", description="执行数学表达式计算，如 '123 + 456'", args_schema=CalculatorSchema)
def calculator(expression: str) -> str:
    """简单安全计算器"""
    try:
        # 只允许基础运算符
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return f"错误: 表达式 '{expression}' 包含不允许的字符"
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"


class WeatherSchema(BaseModel):
    """天气查询参数"""
    city: str


@tool(name="weather", description="查询指定城市的天气", args_schema=WeatherSchema)
def weather(city: str) -> str:
    """模拟天气查询（测试用）"""
    weather_data = {
        "北京": "晴，25°C",
        "上海": "多云，22°C",
        "深圳": "小雨，28°C",
    }
    return weather_data.get(city, f"未找到 {city} 的天气信息，请使用北京/上海/深圳测试")


# ========== 2. 测试工具 ==========

def test_tool_registry():
    """测试工具注册和 schema 生成"""
    print("=" * 60)
    print("测试 1: 工具注册与 Schema 生成")
    print("=" * 60)

    calc_tool = calculator
    print(f"工具实例: {calc_tool}")
    print(f"工具名称: {calc_tool.name}")
    print(f"工具描述: {calc_tool.description}")
    print(f"Schema: {json.dumps(calc_tool.to_openai_schema(), indent=2, ensure_ascii=False)}")

    result = calc_tool.run(expression="100 + 200 * 3")
    print(f"执行结果: {result}")
    print()


# ========== 3. 测试 ReAct Agent ==========

def test_react_agent():
    """测试 ReAct Agent（工具调用循环）"""
    print("=" * 60)
    print("测试 2: ReAct Agent")
    print("=" * 60)

    llm = get_default_qwen_llm()
    agent = ReActAgent(
        llm=llm,
        name="测试助手",
        system_prompt="你是一个测试助手，负责回答问题和调用工具。",
        tools=[calculator, weather],
        memory=InMemoryMemory(),
        max_iterations=5,
    )
    print(f"Agent 信息: {agent}")
    print(f"工具列表: {agent.get_tool_names()}")
    print()

    result = agent.run("北京今天天气怎么样？")
    print(f"输出: {result.output}")
    print(f"耗时: {result.duration_ms}ms")
    print(f"成功: {result.success}")
    print()


# ========== 4. 测试 CoT Agent ==========

def test_cot_agent():
    """测试 CoT Agent（链式推理）"""
    print("=" * 60)
    print("测试 3: CoT Agent")
    print("=" * 60)

    llm = get_default_qwen_llm()
    agent = CoTAgent(
        llm=llm,
        name="推理助手",
        max_iterations=1,
    )
    print(f"Agent 范式: {agent.paradigm}")

    result = agent.run("如果一棵树每年长高 2 米，10 年后它会长高多少米？请逐步推理。")
    print(f"输出: {result.output[:300]}...")
    print(f"耗时: {result.duration_ms}ms")
    print()


# ========== 5. 测试 Plan and Execute Agent ==========

def test_plan_execute_agent():
    """测试 PlanAndExecute Agent"""
    print("=" * 60)
    print("测试 4: PlanAndExecute Agent")
    print("=" * 60)

    llm = get_default_qwen_llm()
    agent = PlanAndExecuteAgent(
        llm=llm,
        name="规划助手",
        tools=[calculator, weather],
        memory=InMemoryMemory(),
        max_iterations=5,
    )
    print(f"Agent 范式: {agent.paradigm}")
    print(f"工具列表: {agent.get_tool_names()}")
    print()

    result = agent.run("帮我比较一下北京、上海、深圳三个城市的天气差异，并计算这三个城市平均温度。")
    print(f"输出: {result.output[:300]}...")
    print(f"耗时: {result.duration_ms}ms")
    print()


# ========== 6. 测试记忆功能 ==========

def test_memory():
    """测试记忆功能"""
    print("=" * 60)
    print("测试 5: 记忆功能")
    print("=" * 60)

    llm = get_default_qwen_llm()
    agent = ReActAgent(
        llm=llm,
        name="记忆助手",
        memory=InMemoryMemory(),
        max_iterations=3,
    )

    # 第一轮对话
    result1 = agent.run("记住我的名字：小明")
    print(f"第一轮: {result1.output}")

    # 第二轮对话（应该能记住名字）
    result2 = agent.run("我叫什么名字？")
    print(f"第二轮: {result2.output}")
    print()


# ========== 主入口 ==========

if __name__ == "__main__":
    test_tool_registry()
    test_react_agent()
    test_cot_agent()
    test_plan_execute_agent()
    test_memory()
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)
