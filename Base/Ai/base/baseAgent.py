"""
Agent 基类与执行范式

提供 Agent 核心能力：绑定 LLM、工具注册/执行、记忆管理、多种执行范式。
"""
import logging
import time
from abc import ABC
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from Base.Ai.base.baseEnum import AgentParadigmEnum
from Base.Ai.base.baseLlm import BaseLlm
from Base.Ai.base.baseTool import BaseTool
from Base.Ai.base.baseMessages import BaseMessages

logger = logging.getLogger(__name__)

UserMessages = BaseMessages.get_user_messages
AssistantMessages = BaseMessages.get_assistant_messages
SystemMessages = BaseMessages.get_system_messages


# ============================================================================
# 记忆模块
# ============================================================================

class BaseMemory(ABC):
    """
    记忆抽象接口

    所有记忆后端必须实现这三个方法。
    """

    def get_messages(self) -> List[Dict[str, Any]]:
        """获取历史消息列表"""
        return []

    def add_message(self, message: Dict[str, Any]):
        """添加一条消息到记忆"""
        pass

    def add_messages(self, messages: List[Dict[str, Any]]):
        """批量添加消息"""
        for msg in messages:
            self.add_message(msg)

    def clear(self):
        """清空记忆"""
        pass


class InMemoryMemory(BaseMemory):
    """
    内存记忆（最简单，默认使用）

    用 List 维护消息历史，适合单轮或少量对话场景。
    """

    def __init__(self, max_messages: int = 50):
        self._messages: List[Dict[str, Any]] = []
        self.max_messages = max_messages

    def get_messages(self) -> List[Dict[str, Any]]:
        return self._messages[-self.max_messages:]

    def add_message(self, message: Dict[str, Any]):
        self._messages.append(message)
        # 超出上限时移除最旧的消息
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def clear(self):
        self._messages.clear()


class DBMemory(BaseMemory):
    """
    数据库记忆（复用已有的 BaseLLMConversationModel 表）

    自动从数据库加载历史对话，并在 Agent 回答后持久化新记录。
    """

    def __init__(
        self,
        user_id: str,
        session_id: str,
        max_turns: int = 10,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.max_turns = max_turns

        # 运行时缓存（避免每次 run 都查库）
        self._cache: Optional[List[Dict[str, Any]]] = None

    def get_messages(self) -> List[Dict[str, Any]]:
        """从数据库加载最近 N 轮对话历史"""
        try:
            from Base.Models.BaseLLMConversationModel import BaseLLMConversationModel
            history = BaseLLMConversationModel.get_last_n_turns_context(
                self.user_id, self.session_id, n=self.max_turns
            )
            self._cache = BaseLLMConversationModel.db_res_2_messages(history)
            return self._cache
        except Exception as e:
            logger.warning(f"DBMemory 加载历史失败: {e}")
            return []

    def add_message(self, message: Dict[str, Any]):
        """DBMemory 不需要手动 add_message，持久化由 Agent 在 run 结束后统一处理"""
        pass

    def save_conversation(
        self,
        question: str,
        answer: str,
        ai_model: str = None,
        ai_agent: str = None,
        status: str = "success",
        error_msg: str = None,
        duration_ms: int = 0,
    ):
        """持久化一轮对话到数据库"""
        try:
            from Base.Models.BaseLLMConversationModel import BaseLLMConversationModel
            conv = BaseLLMConversationModel(
                question=question,
                answer=answer,
                user_id=self.user_id,
                session_id=self.session_id,
                ai_model=ai_model,
                ai_agent=ai_agent,
                stream_mode="0",
                source="agent",
                status=status,
                error_msg=error_msg,
                duration_ms=duration_ms,
            )
            conv.save()
            logger.debug(f"DBMemory 持久化对话成功: conversation_id={conv.id}")
        except Exception as e:
            logger.error(f"DBMemory 持久化对话失败: {e}", exc_info=True)

    def clear(self):
        """DBMemory 不支持 clear 操作（数据在数据库中）"""
        pass


# ============================================================================
# Agent 运行结果
# ============================================================================

class AgentResult(BaseModel):
    """Agent 单次运行的结果"""
    success: bool = True
    output: str = ""
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    iterations: int = 0
    duration_ms: int = 0
    error_msg: Optional[str] = None


# ============================================================================
# Agent 基类
# ============================================================================

class BaseAgent(ABC):
    """
    Agent 抽象基类

    核心能力：
    - 绑定 BaseLlm 作为基座模型
    - 注册 / 执行工具（OpenAI function calling）
    - 记忆管理（内存 / 数据库）
    - 可扩展的执行范式（通过子类覆写 _run_loop）
    """

    def __init__(
        self,
        llm: BaseLlm,
        name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[BaseMemory] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        max_iterations: int = 10,
        paradigm: Optional[AgentParadigmEnum] = None,
        **kwargs: Any,
    ):
        """
        初始化 Agent

        Args:
            llm: 基座 LLM 实例（必须）
            name: Agent 名称
            system_prompt: 系统提示词
            tools: 初始工具列表
            memory: 记忆后端（不传则使用 InMemoryMemory）
            user_id: 用户 ID（用于 DBMemory）
            session_id: 会话 ID（用于 DBMemory）
            max_iterations: 单次运行最大循环次数（防止死循环）
            paradigm: 执行范式
        """
        self.llm = llm
        self.name = name or self.__class__.__name__
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.paradigm = paradigm

        # 工具管理
        self._tools: Dict[str, BaseTool] = {}
        if tools:
            for t in tools:
                self.add_tool(t)

        # 记忆管理
        if memory:
            self.memory = memory
        elif user_id and session_id:
            self.memory = DBMemory(user_id=user_id, session_id=session_id)
        else:
            self.memory = InMemoryMemory()

    # ---- 工具管理 ----

    def add_tool(self, tool: BaseTool):
        """注册单个工具"""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"tool 必须是 BaseTool 实例，而非 {type(tool)}")
        self._tools[tool.name] = tool
        logger.debug(f"Agent [{self.name}] 注册工具: {tool.name}")

    def add_tools(self, *tools: BaseTool):
        """批量注册工具"""
        for t in tools:
            self.add_tool(t)

    def remove_tool(self, name: str):
        """移除工具"""
        self._tools.pop(name, None)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具实例"""
        return self._tools.get(name)

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回所有工具的 OpenAI schema，用于 chat 调用的 tools 参数"""
        return [t.to_openai_schema() for t in self._tools.values()]

    # ---- 记忆管理 ----

    def clear_memory(self):
        """清空记忆"""
        self.memory.clear()

    # ---- 入口方法 ----

    def run(self, user_input: str, **kwargs: Any) -> AgentResult:
        """
        同步执行 Agent

        Args:
            user_input: 用户输入
            **kwargs: 额外参数（会传给 _run_loop）

        Returns:
            AgentResult 运行结果
        """
        start_time = time.time()
        result = AgentResult()

        try:
            messages = self._build_messages(user_input)
            logger.info(f"Agent [{self.name}] 开始执行, 范式: {self.paradigm}")

            output = self._run_loop(messages, **kwargs)
            result.output = output
            result.success = True

            logger.info(f"Agent [{self.name}] 执行完成, 输出长度: {len(output)}")

        except Exception as e:
            logger.error(f"Agent [{self.name}] 执行失败: {e}", exc_info=True)
            result.success = False
            result.error_msg = str(e)
            result.output = f"执行出错: {str(e)}"

        result.duration_ms = int((time.time() - start_time) * 1000)
        return result

    async def arun(self, user_input: str, **kwargs: Any) -> AgentResult:
        """
        异步执行 Agent

        Args:
            user_input: 用户输入
            **kwargs: 额外参数

        Returns:
            AgentResult 运行结果
        """
        start_time = time.time()
        result = AgentResult()

        try:
            messages = self._build_messages(user_input)
            logger.info(f"Agent [{self.name}] 异步开始执行, 范式: {self.paradigm}")

            output = await self._arun_loop(messages, **kwargs)
            result.output = output
            result.success = True

        except Exception as e:
            logger.error(f"Agent [{self.name}] 异步执行失败: {e}", exc_info=True)
            result.success = False
            result.error_msg = str(e)
            result.output = f"执行出错: {str(e)}"

        result.duration_ms = int((time.time() - start_time) * 1000)
        return result

    # ---- 内部方法 ----

    def _build_messages(self, user_input: str) -> List[Dict[str, Any]]:
        """
        构建完整消息列表

        顺序：system_prompt → memory → user_input

        Args:
            user_input: 用户输入

        Returns:
            消息列表
        """
        messages = []

        # 1. 系统提示词
        prompt = self.system_prompt or self._default_system_prompt()
        messages.append(SystemMessages(prompt=prompt))

        # 2. 记忆历史
        memory_messages = self.memory.get_messages()
        if memory_messages:
            messages.extend(memory_messages)

        # 3. 当前用户输入
        messages.append(UserMessages(prompt=user_input))

        return messages

    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        tools_info = ""
        if self._tools:
            tool_names = ", ".join(self._tools.keys())
            tools_info = f"\n\n你可用的工具: {tool_names}。请根据需要选择合适的工具。"

        return f"你是一个名为 {self.name} 的 AI 助手。请根据用户的问题，给出有帮助的回答。{tools_info}"

    def _run_loop(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """
        执行范式主循环（默认实现：最简工具调用循环）

        子类可通过覆写此方法实现不同的执行范式。

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            最终输出文本
        """
        messages = list(messages)  # 拷贝，避免修改原列表
        iteration = 0
        final_text = ""

        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Agent [{self.name}] 第 {iteration} 轮循环")

            # 调用 LLM
            response = self._call_llm(messages)

            # 检查是否有 tool_calls
            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                # 没有工具调用，返回最终文本
                final_text = self._extract_text_content(response)
                break

            # 执行工具
            for tc in tool_calls:
                tool_result = self._execute_tool_call(tc)
                messages.append({
                    "role": "tool",
                    "content": str(tool_result),
                    "tool_call_id": tc.get("id", ""),
                })

        # 将最终回答加入记忆
        self.memory.add_message(AssistantMessages(prompt=final_text))

        return final_text

    async def _arun_loop(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """
        异步执行范式主循环（默认实现）

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            最终输出文本
        """
        messages = list(messages)
        iteration = 0
        final_text = ""

        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"Agent [{self.name}] 异步第 {iteration} 轮循环")

            response = await self._acall_llm(messages)

            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                final_text = self._extract_text_content(response)
                break

            for tc in tool_calls:
                tool_result = await self._aexecute_tool_call(tc)
                messages.append({
                    "role": "tool",
                    "content": str(tool_result),
                    "tool_call_id": tc.get("id", ""),
                })

        self.memory.add_message(AssistantMessages(prompt=final_text))

        return final_text

    # ---- LLM 调用 ----

    def _call_llm(self, messages: List[Dict[str, Any]]) -> Any:
        """
        调用 LLM（带 tools 参数）

        Args:
            messages: 消息列表

        Returns:
            OpenAI ChatCompletion 响应对象
        """
        tools = self.get_tool_schemas() if self._tools else None
        kwargs: Dict[str, Any] = {
            "model": self.llm.model_name,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        return self.llm.model_client.chat.completions.create(**kwargs)

    async def _acall_llm(self, messages: List[Dict[str, Any]]) -> Any:
        """
        异步调用 LLM

        Args:
            messages: 消息列表

        Returns:
            OpenAI ChatCompletion 响应对象
        """
        tools = self.get_tool_schemas() if self._tools else None
        kwargs: Dict[str, Any] = {
            "model": self.llm.model_name,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        return await self.llm.async_model_client.chat.completions.create(**kwargs)

    # ---- 响应解析 ----

    def _extract_tool_calls(self, response) -> List[Dict[str, Any]]:
        """
        从 LLM 响应中提取 tool_calls

        Args:
            response: OpenAI ChatCompletion 对象

        Returns:
            tool_calls 列表，如果没有则返回空列表
        """
        message = response.choices[0].message
        if hasattr(message, "tool_calls") and message.tool_calls:
            return [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in message.tool_calls
            ]
        return []

    @staticmethod
    def _extract_text_content(response) -> str:
        """
        从 LLM 响应中提取文本内容

        Args:
            response: OpenAI ChatCompletion 对象

        Returns:
            文本内容
        """
        content = response.choices[0].message.content
        return content or ""

    # ---- 工具执行 ----

    def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Any:
        """
        执行单个工具调用

        Args:
            tool_call: {"id": "...", "name": "...", "arguments": "..."}

        Returns:
            工具执行结果
        """
        import json

        tool_name = tool_call["name"]
        tool_args = json.loads(tool_call["arguments"]) if isinstance(tool_call["arguments"], str) else tool_call["arguments"]

        tool = self._tools.get(tool_name)
        if not tool:
            return f"错误: 未找到工具 '{tool_name}'"

        return tool.run(**tool_args)

    async def _aexecute_tool_call(self, tool_call: Dict[str, Any]) -> Any:
        """异步执行单个工具调用"""
        import json

        tool_name = tool_call["name"]
        tool_args = json.loads(tool_call["arguments"]) if isinstance(tool_call["arguments"], str) else tool_call["arguments"]

        tool = self._tools.get(tool_name)
        if not tool:
            return f"错误: 未找到工具 '{tool_name}'"

        return await tool.arun(**tool_args)

    def __repr__(self):
        return (
            f"Agent(name='{self.name}', llm='{self.llm.model_name}', "
            f"tools={self.get_tool_names()}, paradigm={self.paradigm})"
        )


# ============================================================================
# 范式子类
# ============================================================================

class ReActAgent(BaseAgent):
    """
    ReAct 范式 Agent

    Reason + Act 循环：
    1. LLM 推理并决定是否调用工具
    2. 如果有 tool_calls，执行工具并将结果追加到对话
    3. 重复直到 LLM 不再请求工具调用，返回最终答案

    这是最常用、最基础的 Agent 范式。
    """

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("paradigm", AgentParadigmEnum.REACT)
        super().__init__(**kwargs)

    def _default_system_prompt(self) -> str:
        tools_info = ""
        if self._tools:
            tools_desc = []
            for t in self._tools.values():
                tools_desc.append(f"- {t.name}: {t.description}")
            tools_info = (
                "\n\n你可用的工具如下：\n"
                + "\n".join(tools_desc)
                + "\n\n当需要用到工具时，请调用对应的工具函数。"
            )

        return (
            f"你是一个名为 {self.name} 的 AI 助手。"
            f"请根据用户的问题，进行逐步推理和工具调用。"
            f"你可以多次调用工具来获取必要的信息，直到你能给出准确的答案。"
            f"{tools_info}"
        )


class CoTAgent(BaseAgent):
    """
    Chain of Thought 范式 Agent

    通过在系统提示词中强制模型逐步推理，适用于需要复杂推理的场景。
    不使用工具调用，只做深度推理。
    """

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("paradigm", AgentParadigmEnum.COT)
        super().__init__(**kwargs)

    def _default_system_prompt(self) -> str:
        return (
            f"你是一个名为 {self.name} 的 AI 助手。"
            f"请逐步思考问题，展示你的推理过程，然后给出最终答案。\n"
            f"请按照以下格式回答：\n"
            f"1. 首先，分析问题...\n"
            f"2. 然后，逐步推理...\n"
            f"3. 最后，给出结论。\n"
        )

    def _run_loop(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """CoT 不需要工具调用，单次 LLM 调用即可"""
        response = self._call_llm(messages)
        final_text = self._extract_text_content(response)
        self.memory.add_message(AssistantMessages(prompt=final_text))
        return final_text

    async def _arun_loop(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """CoT 异步执行"""
        response = await self._acall_llm(messages)
        final_text = self._extract_text_content(response)
        self.memory.add_message(AssistantMessages(prompt=final_text))
        return final_text


class PlanAndExecuteAgent(BaseAgent):
    """
    Plan and Execute 范式 Agent

    两阶段执行：
    1. Plan: 让 LLM 根据用户输入生成一个执行计划（步骤列表）
    2. Execute: 按照计划逐步执行，每一步都可以调用工具
    3. Synthesize: 汇总所有步骤的结果，生成最终答案

    适用于复杂任务，需要多个工具协调完成。
    """

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("paradigm", AgentParadigmEnum.PLAN_AND_EXECUTE)
        super().__init__(**kwargs)

    def _default_system_prompt(self) -> str:
        tools_info = ""
        if self._tools:
            tools_desc = []
            for t in self._tools.values():
                tools_desc.append(f"- {t.name}: {t.description}")
            tools_info = (
                "\n\n你可用的工具如下：\n"
                + "\n".join(tools_desc)
                + "\n\n在执行步骤时，可以根据需要调用工具。"
            )

        return (
            f"你是一个名为 {self.name} 的 AI 助手。"
            f"你需要根据用户的请求，先制定一个详细的执行计划，"
            f"然后按照计划逐步执行，最终给出完整的答案。{tools_info}"
        )

    def _run_loop(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        # Phase 1: 生成计划
        plan_messages = list(messages)
        plan_messages.append(UserMessages(prompt="请先制定一个详细的执行计划，列出你需要完成的步骤。"))

        plan_response = self._call_llm(plan_messages)
        plan = self._extract_text_content(plan_response)
        logger.info(f"Agent [{self.name}] 执行计划:\n{plan}")

        # Phase 2: 执行每个步骤
        messages = list(messages)
        messages.append(AssistantMessages(prompt=f"我的执行计划如下：\n{plan}\n现在我开始逐步执行。"))

        step_results = []
        step_num = 1

        # 解析计划中的步骤（简单按行分割）
        steps = [line.strip() for line in plan.split("\n") if line.strip() and len(line.strip()) > 5]

        for step_desc in steps[:self.max_iterations]:
            step_messages = list(messages)
            step_messages.append(UserMessages(prompt=f"执行第 {step_num} 步：{step_desc}"))

            step_response = self._call_llm(step_messages)
            tool_calls = self._extract_tool_calls(step_response)

            if tool_calls:
                for tc in tool_calls:
                    tool_result = self._execute_tool_call(tc)
                    step_messages.append({
                        "role": "tool",
                        "content": str(tool_result),
                        "tool_call_id": tc.get("id", ""),
                    })

            step_output = self._extract_text_content(step_response)
            step_results.append(f"步骤 {step_num} ({step_desc}):\n{step_output}")
            messages.append(AssistantMessages(prompt=f"步骤 {step_num} 完成: {step_output}"))
            step_num += 1

        # Phase 3: 汇总结果
        summary_messages = list(messages)
        summary_content = "\n\n".join(step_results)
        summary_messages.append(UserMessages(prompt=f"所有步骤已完成。请根据以下执行结果，给出最终答案：\n\n{summary_content}"))

        summary_response = self._call_llm(summary_messages)
        final_text = self._extract_text_content(summary_response)

        self.memory.add_message(AssistantMessages(prompt=final_text))
        return final_text

    async def _arun_loop(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        # Phase 1: 生成计划
        plan_messages = list(messages)
        plan_messages.append(UserMessages(prompt="请先制定一个详细的执行计划，列出你需要完成的步骤。"))

        plan_response = await self._acall_llm(plan_messages)
        plan = self._extract_text_content(plan_response)

        # Phase 2: 执行每个步骤
        messages = list(messages)
        messages.append(AssistantMessages(prompt=f"我的执行计划如下：\n{plan}\n现在我开始逐步执行。"))

        step_results = []
        step_num = 1

        steps = [line.strip() for line in plan.split("\n") if line.strip() and len(line.strip()) > 5]

        for step_desc in steps[:self.max_iterations]:
            step_messages = list(messages)
            step_messages.append(UserMessages(prompt=f"执行第 {step_num} 步：{step_desc}"))

            step_response = await self._acall_llm(step_messages)
            tool_calls = self._extract_tool_calls(step_response)

            if tool_calls:
                for tc in tool_calls:
                    tool_result = await self._aexecute_tool_call(tc)
                    step_messages.append({
                        "role": "tool",
                        "content": str(tool_result),
                        "tool_call_id": tc.get("id", ""),
                    })

            step_output = self._extract_text_content(step_response)
            step_results.append(f"步骤 {step_num} ({step_desc}):\n{step_output}")
            messages.append(AssistantMessages(prompt=f"步骤 {step_num} 完成: {step_output}"))
            step_num += 1

        # Phase 3: 汇总结果
        summary_messages = list(messages)
        summary_content = "\n\n".join(step_results)
        summary_messages.append(UserMessages(prompt=f"所有步骤已成。请根据以下执行结果，给出最终答案：\n\n{summary_content}"))

        summary_response = await self._acall_llm(summary_messages)
        final_text = self._extract_text_content(summary_response)

        self.memory.add_message(AssistantMessages(prompt=final_text))
        return final_text
