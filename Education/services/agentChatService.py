import json
import logging
import time
from typing import Optional, AsyncGenerator, ClassVar, Dict
from pydantic import BaseModel, Field

from Base.Ai.base import SystemMessages, UserMessages
from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.RicUtils.httpUtils import HttpResponse
from Base.Models.BaseLLMConversationModel import BaseLLMConversationModel
from Base.Service.llmConversationService import save_conversation_from_db_2_vdb
from Base.Service.memoryV1Service import MemoryV1Service
from Base.Models.BaseLLMSession import BaseLLMSession
from Education.prompts.agentPrompts import (
    get_intent_recognition_messages,
    GENERATE_QUESTION_SYSTEM_PROMPT,
    JUDGE_ANSWER_SYSTEM_PROMPT,
    EXPLAIN_QUESTION_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    RECOMMEND_SYSTEM_PROMPT,
    LEARNING_PROGRESS_SYSTEM_PROMPT
)
from Education.services.questionService import get_question_service
from Education.services.userProfileService import get_user_profile_service
from Education.models.pojo.questionBo import QuestionRandomBo, AiJudgeQuestionBo
from Education.models.pojo.questionPo import QuestionPo
from Education.models.pojo.agentChatBo import (
    IntentRecognitionResult,
    GenerateQuestionParams,
    JudgeAnswerParams,
    ExplainQuestionParams,
    ChatParams,
    RecommendQuestionsParams,
    LearningProgressParams
)

logger = logging.getLogger(__name__)


# ========== 会话上下文管理 ==========
class SessionContext(BaseModel):
    """会话上下文，用于保存当前题目信息"""
    session_id: str
    user_id: str
    current_question_id: Optional[str] = None
    current_question_text: Optional[str] = None
    last_question_id: Optional[str] = None
    last_update_time: float = Field(default_factory=time.time)


# 内存中的会话上下文缓存 (user_id -> SessionContext)
_session_contexts: Dict[str, SessionContext] = {}

# 题目数据缓存 (question_id -> question_data)
# 用于临时存储刚生成的题目数据，便于判题时使用
_question_cache: Dict[str, dict] = {}


def get_session_context(user_id: str, session_id: Optional[str] = None) -> Optional[SessionContext]:
    """获取用户的会话上下文"""
    if not user_id:
        return None

    # 优先使用 session_id 作为 key
    key = f"{user_id}:{session_id}" if session_id else user_id

    if key in _session_contexts:
        ctx = _session_contexts[key]
        # 检查是否过期（30 分钟）
        if time.time() - ctx.last_update_time < 1800:
            return ctx
        else:
            # 过期删除
            del _session_contexts[key]
    return None


def set_session_context(user_id: str, question_id: str, question_text: str, session_id: Optional[str] = None):
    """设置用户的会话上下文（当前题目信息）"""
    key = f"{user_id}:{session_id}" if session_id else user_id

    _session_contexts[key] = SessionContext(
        session_id=session_id or '',
        user_id=user_id,
        current_question_id=question_id,
        current_question_text=question_text,
        last_update_time=time.time()
    )


def clear_session_context(user_id: str, session_id: Optional[str] = None):
    """清除用户的会话上下文"""
    key = f"{user_id}:{session_id}" if session_id else user_id
    if key in _session_contexts:
        del _session_contexts[key]


# ========== AgentChatService ==========
class AgentChatService(BaseModel):
    """
    Agent 聊天服务
    负责意图识别、意图分发、会话管理
    """

    # 意图处理器映射表
    INTENT_HANDLERS: ClassVar[Dict[str, str]] = {
        'generate_question': 'handle_generate_question',
        'judge_answer': 'handle_judge_answer',
        'explain_question': 'handle_explain_question',
        'chat': 'handle_chat',
        'recommend_questions': 'handle_recommend_questions',
        'learning_progress': 'handle_learning_progress',
    }

    def recognize_intent(
        self,
        user_input: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        history_n: int = 3
    ) -> IntentRecognitionResult:
        """
        识别用户意图

        Args:
            user_input: 用户输入
            user_id: 用户 ID
            session_id: 会话 ID
            history_n: 历史对话轮数，默认 3 轮

        Returns:
            意图识别结果
        """
        try:
            messages = get_intent_recognition_messages(user_input, user_id, session_id, history_n)
            llm = get_default_qwen_llm()
            response = llm.chat(messages)

            # 清理响应文本，提取 JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()

            # 解析 JSON
            intent_data = json.loads(response)

            return IntentRecognitionResult(
                intent=intent_data.get('intent', 'chat'),
                confidence=float(intent_data.get('confidence', 0.5)),
                params=intent_data.get('params', {}),
                reason=intent_data.get('reason', '')
            )

        except Exception as e:
            logger.error(f"意图识别失败：{str(e)}")
            # 识别失败时返回默认聊天意图
            return IntentRecognitionResult(
                intent='chat',
                confidence=0.5,
                params={},
                reason=f"意图识别异常，使用默认聊天意图：{str(e)}"
            )

    async def handle_request(
        self,
        user_input: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        is_stream: bool = False,
        is_thinking: bool = False,
        current_question_id: Optional[str] = None,
        current_question_text: Optional[str] = None
    ) -> dict | AsyncGenerator:
        """
        处理 Agent 聊天请求

        Args:
            user_input: 用户输入
            user_id: 用户 ID
            session_id: 会话 ID（前端传入的 session_id，用于内存上下文）
            is_stream: 是否流式输出
            is_thinking: 是否思考模式
            current_question_id: 当前题目 ID
            current_question_text: 当前题目文本

        Returns:
            响应字典或流式生成器
        """
        start_time = time.time()

        # 1. 获取或创建 session（先获取 session，用于后续意图识别的历史对话查询）
        db_session_id = None
        effective_session_id = session_id  # 用于意图识别和历史记忆的有效 session_id
        if user_id:
            try:
                session = BaseLLMSession.get_user_last_session(user_id, session_id)
                if session:
                    db_session_id = session.session_uuid
                    effective_session_id = session.session_uuid  # 使用数据库 session 的 UUID
                    logger.debug(f"获取到用户 session: user_id={user_id}, session_uuid={db_session_id}")
                else:
                    session = BaseLLMSession.get_or_create_session(user_id=user_id)
                    db_session_id = session.session_uuid
                    effective_session_id = session.session_uuid
                    logger.warning(f"get_user_last_session 返回 None，已创建新 session: session_uuid={db_session_id}")
            except Exception as e:
                logger.error(f"获取 session 失败：{str(e)}")
                try:
                    session = BaseLLMSession.get_or_create_session(user_id=user_id)
                    db_session_id = session.session_uuid
                    effective_session_id = session.session_uuid
                    logger.warning(f"获取 session 异常，已创建新 session: session_uuid={db_session_id}")
                except Exception as create_error:
                    logger.error(f"创建 session 也失败：{str(create_error)}")
                    db_session_id = None
                    effective_session_id = session_id
        else:
            effective_session_id = session_id

        # 2. 意图识别（传入 user_id 和 effective_session_id，用于获取历史对话上下文）
        intent_result = self.recognize_intent(user_input, user_id, effective_session_id, history_n=3)
        logger.info(f"意图识别结果：{intent_result}")

        # 3. 参数补充
        if current_question_id and 'question_id' not in intent_result.params:
            intent_result.params['question_id'] = current_question_id
        if current_question_text and 'question_text' not in intent_result.params:
            intent_result.params['question_text'] = current_question_text

        # 4. 获取对应的处理器
        handler_method = self.INTENT_HANDLERS.get(intent_result.intent, 'handle_chat')
        handler = getattr(self, handler_method, self.handle_chat)

        # 5. 执行处理器
        try:
            # 异步更新用户画像（不阻塞响应）
            if user_id:
                self._update_profile_async(intent_result, user_id, user_input)

            # 如果是流式输出，返回流式生成器（持久化在 _stream_handler_wrapper 中处理）
            if is_stream:
                return self._stream_handler_wrapper(
                    handler=handler,
                    user_input=user_input,
                    intent_result=intent_result,
                    user_id=user_id,
                    session_id=db_session_id,  # 使用从 session 表获取的 session_uuid
                    is_thinking=is_thinking
                )

            # 非流式输出：执行处理器并持久化
            result = await handler(
                user_input=user_input,
                intent_result=intent_result,
                user_id=user_id,
                session_id=db_session_id  # 使用从 session 表获取的 session_uuid
            )

            # 持久化对话记录
            answer = result.get('answer', '') if isinstance(result, dict) else str(result)

            # 获取记忆上下文（使用原始 session_id 用于内存上下文查找）
            try:
                memory_context = MemoryV1Service.get_simple_memory(
                    question=user_input,
                    user_id=user_id,
                    session_id=session_id  # 内存上下文使用前端传入的 session_id
                )
                context = str(memory_context)
            except Exception as e:
                logger.warning(f"获取记忆上下文失败：{str(e)}")
                context = ''

            conversation = BaseLLMConversationModel(
                question=user_input,
                user_id=user_id,
                session_id=db_session_id,  # 持久化使用从 session 表获取的 session_uuid
                answer=answer,
                context=context,
                ai_model='qwen',
                ai_agent='小 e 做题 Agent',
                stream_mode='0',
                source='edu_agent_chat',
                status='success',
                duration_ms=int((time.time() - start_time) * 1000)
            )
            conversation.save()

            # 保存到向量数据库
            try:
                save_conversation_from_db_2_vdb(conversation)
            except Exception as vdb_error:
                logger.warning(f"保存到 VDB 失败：{str(vdb_error)}")

            logger.info(f"对话持久化完成：conversation_id={conversation.id}, answer_length={len(conversation.answer)}, session_id={db_session_id}")

            return result

        except Exception as e:
            logger.error(f"意图处理失败：{str(e)}")
            # 异常时也尝试持久化错误记录
            if user_id:
                try:
                    error_conversation = BaseLLMConversationModel(
                        question=user_input,
                        user_id=user_id,
                        session_id=db_session_id,
                        answer=f"抱歉，处理您的请求时出现错误：{str(e)}",
                        ai_model='qwen',
                        ai_agent='小 e 做题 Agent',
                        stream_mode='1' if is_stream else '0',
                        source='edu_agent_chat',
                        status='failed',
                        error_msg=str(e),
                        duration_ms=int((time.time() - start_time) * 1000)
                    )
                    error_conversation.save()
                    logger.info(f"错误记录已持久化：conversation_id={error_conversation.id}")
                except Exception as save_error:
                    logger.error(f"持久化错误记录失败：{str(save_error)}")

            if is_stream:
                return self._error_stream_handler(f"抱歉，处理您的请求时出现错误：{str(e)}")
            return {
                'intent': intent_result.intent,
                'answer': f"抱歉，处理您的请求时出现错误：{str(e)}",
                'data': None
            }

    def _update_profile_async(self, intent_result: IntentRecognitionResult, user_id: str, user_input: str):
        """
        异步更新用户画像

        Args:
            intent_result: 意图识别结果
            user_id: 用户 ID
            user_input: 用户输入
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        executor = ThreadPoolExecutor(max_workers=1)

        def update_task():
            try:
                service = get_user_profile_service()
                service.update_profile_from_chat(
                    user_id=user_id,
                    intent=intent_result.intent,
                    question=user_input
                )
                logger.debug(f"用户画像已异步更新：user_id={user_id}, intent={intent_result.intent}")
            except Exception as e:
                logger.error(f"异步更新用户画像失败：{str(e)}")

        # 在线程池中执行
        executor.submit(update_task)

    async def _stream_handler_wrapper(
        self,
        handler,
        user_input: str,
        intent_result: IntentRecognitionResult,
        user_id: Optional[str],
        session_id: Optional[str],
        is_thinking: bool
    ) -> AsyncGenerator:
        """
        流式处理器包装器 - 支持真正的流式输出 + 持久化

        Args:
            handler: 处理器函数
            user_input: 用户输入
            intent_result: 意图识别结果
            user_id: 用户 ID
            session_id: 会话 ID
            is_thinking: 是否思考模式
        """
        start_time = time.time()

        # 初始化对话记录
        conversation = BaseLLMConversationModel(
            question=user_input,
            user_id=user_id,
            session_id=session_id,
            ai_model='qwen',
            ai_agent='小 e 做题 Agent',
            stream_mode='1',
            source='edu_agent_chat'
        )

        # 获取记忆上下文
        try:
            memory_context = MemoryV1Service.get_simple_memory(
                question=user_input,
                user_id=user_id,
                session_id=session_id
            )
            conversation.context = str(memory_context)
        except Exception as e:
            logger.warning(f"获取记忆上下文失败：{str(e)}")
            conversation.context = ''

        content_parts = []
        reasoning_parts = []

        try:
            # 思考模式：先输出思考过程
            if is_thinking:
                thinking_content = f"我正在分析您的问题，识别到的意图是：{intent_result.intent}"
                if intent_result.reason:
                    thinking_content += f"，因为{intent_result.reason}"

                yield {
                    'type': 'reasoning',
                    'content': thinking_content
                }
                reasoning_parts.append(thinking_content)

            # 检查 handler 是否有流式版本
            stream_handler = getattr(self, f'{handler.__name__}_stream', None)
            if stream_handler:
                # 使用流式版本
                async for chunk in stream_handler(
                    user_input=user_input,
                    intent_result=intent_result,
                    user_id=user_id,
                    session_id=session_id
                ):
                    yield {
                        'type': 'content',
                        'content': chunk
                    }
                    content_parts.append(chunk)
            else:
                # 降级为非流式：先执行处理器获取结果，然后逐字分块输出
                result = await handler(
                    user_input=user_input,
                    intent_result=intent_result,
                    user_id=user_id,
                    session_id=session_id
                )
                answer = result.get('answer', '') if isinstance(result, dict) else str(result)

                # 先输出一个开始标记
                yield {
                    'type': 'content_start',
                    'content': ''
                }

                # 逐字输出（每 5 个字符一个 chunk，避免太小）
                import asyncio
                chunk_size = 5
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i + chunk_size]
                    yield {
                        'type': 'content',
                        'content': chunk
                    }
                    content_parts.append(chunk)
                    # 添加微小延迟以模拟流式效果
                    await asyncio.sleep(0.01)

                # 输出结束标记
                yield {
                    'type': 'content_end',
                    'content': ''
                }

            # 流式输出完成后，持久化
            conversation.answer = ''.join(content_parts)
            conversation.status = 'success'
            conversation.duration_ms = int((time.time() - start_time) * 1000)
            conversation.save()

            # 保存到向量数据库
            try:
                save_conversation_from_db_2_vdb(conversation)
            except Exception as vdb_error:
                logger.warning(f"保存到 VDB 失败：{str(vdb_error)}")

            logger.info(f"对话持久化完成：conversation_id={conversation.id}, answer_length={len(conversation.answer)}")

        except Exception as e:
            logger.error(f"流式处理失败：{str(e)}")
            conversation.status = 'failed'
            conversation.error_msg = str(e)
            conversation.duration_ms = int((time.time() - start_time) * 1000)
            conversation.save()

            yield {
                'type': 'error',
                'content': f"抱歉，流式输出时出现错误：{str(e)}"
            }

    async def handle_chat_stream(
        self,
        user_input: str,
        intent_result: IntentRecognitionResult,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> AsyncGenerator:
        """
        处理聊天意图（流式版本）

        Yields:
            文本片段
        """
        # 获取记忆上下文
        context = MemoryV1Service.get_simple_memory(
            question=user_input,
            user_id=user_id,
            session_id=session_id
        )

        # 构建对话 messages
        messages = context + [UserMessages(prompt=user_input)]

        llm = get_default_qwen_llm()

        # 使用流式调用用来实现真正的流式输出
        import asyncio

        # 在后台执行异步流式调用
        loop = asyncio.get_event_loop()

        # 使用 run_in_executor 执行同步的流式调用
        def sync_chat_stream():
            stream = llm.chat(messages, stream=True)
            for chunk in stream:
                yield chunk

        # 执行流式输出
        for chunk in sync_chat_stream():
            yield chunk

    async def _error_stream_handler(self, error_message: str) -> AsyncGenerator:
        """
        错误流式处理器

        Args:
            error_message: 错误信息
        """
        yield {
            'type': 'error',
            'content': error_message
        }

    async def _stream_handler(
        self,
        result: dict,
        intent_result: IntentRecognitionResult,
        is_thinking: bool
    ) -> AsyncGenerator:
        """
        流式处理器包装器（已废弃，保留用于兼容性）

        Args:
            result: 处理结果
            intent_result: 意图识别结果
            is_thinking: 是否思考模式
        """
        try:
            # 将结果转换为流式输出
            answer = result.get('answer', '') if isinstance(result, dict) else str(result)

            if is_thinking:
                # 思考模式：先输出思考过程
                thinking_content = f"我正在分析您的问题，识别到的意图是：{intent_result.intent}"
                if intent_result.reason:
                    thinking_content += f"，因为{intent_result.reason}"

                yield {
                    'type': 'reasoning',
                    'content': thinking_content
                }

            # 输出答案
            yield {
                'type': 'content',
                'content': answer
            }

        except Exception as e:
            logger.error(f"流式处理失败：{str(e)}")
            yield {
                'type': 'error',
                'content': f"抱歉，流式输出时出现错误：{str(e)}"
            }

    async def handle_generate_question(
        self,
        user_input: str,
        intent_result: IntentRecognitionResult,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> dict:
        """
        处理出题意图
        """
        params = intent_result.params

        # 构建出题参数
        question_bo = QuestionRandomBo(
            subject=params.get('subject'),
            question_type=params.get('question_type'),
            difficulty_level=params.get('difficulty_level'),
            grade_type=params.get('grade_type')
        )

        # 调用出题服务
        question_service = get_question_service()
        question_data = question_service.random_generate_question(question_bo)

        # 获取题目 ID 和文本
        # question_data 是 LLM 生成的原始数据，question_uuid 可能还没有（因为是先生成后保存）
        # 我们优先使用 question_uuid，如果没有，则临时生成一个唯一的 session key
        question_uuid = question_data.get('question_uuid', '')
        question_text = question_data.get('question_text', '')

        # 生成一个临时的题目标识符（用于会话记忆）
        # 格式：question_{user_id}_{timestamp}
        temp_question_id = f"question_{user_id}_{int(time.time())}" if user_id else None

        # 保存到会话上下文（优先使用 question_uuid，否则使用临时 ID）
        if user_id:
            context_question_id = question_uuid or temp_question_id
            set_session_context(
                user_id=user_id,
                question_id=context_question_id,
                question_text=question_text,
                session_id=session_id
            )
            logger.info(f"已保存题目到会话上下文：user_id={user_id}, question_id={context_question_id}")

            # 同时将题目数据缓存起来，便于判题时使用
            _question_cache[context_question_id] = {
                'question_text': question_text,
                'question_data': question_data,
                'created_at': time.time()
            }

        # 构建回复
        answer = f"好的，我已经为您生成了一道题目：\n\n{question_text}"

        return {
            'intent': 'generate_question',
            'answer': answer,
            'data': question_data,
            'session_id': session_id
        }

    async def handle_judge_answer(
        self,
        user_input: str,
        intent_result: IntentRecognitionResult,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> dict:
        """
        处理判题意图
        """
        params = intent_result.params
        question_id = params.get('question_id')

        # 优先从会话上下文获取题目 ID（实现记忆功能）
        if not question_id and user_id:
            ctx = get_session_context(user_id, session_id)
            if ctx and ctx.current_question_id:
                question_id = ctx.current_question_id
                logger.info(f"从会话上下文获取题目 ID: {question_id}")

        # 如果还是没有题目 ID，尝试从 API 传入的参数获取
        if not question_id:
            question_id = params.get('current_question_id')

        if not question_id:
            return {
                'intent': 'judge_answer',
                'answer': "请提供要判题的题目 ID，或者先选择一道题目。",
                'data': None
            }

        # 提取用户答案：优先使用 params 中的 answer，如果没有则从用户输入中提取
        answer = params.get('answer')
        if not answer:
            # 从用户输入中提取答案（处理"我选 A"、"答案是 B"等简短回答）
            answer = self._extract_answer_from_input(user_input)
        if not answer:
            answer = user_input

        # 检查是否是临时题目 ID（格式：question_{user_id}_{timestamp}）
        is_temp_question = question_id.startswith('question_')

        if is_temp_question and user_id:
            # 从缓存中获取题目数据
            cached = _question_cache.get(question_id)
            if cached:
                question_data = cached.get('question_data', {})
                logger.info(f"从缓存获取题目数据：question_id={question_id}")
            else:
                # 缓存过期或不存在
                return {
                    'intent': 'judge_answer',
                    'answer': "抱歉，题目数据已过期，请重新生成题目后再提交答案。",
                    'data': None
                }
        else:
            # 从数据库获取题目
            question_data = None

        # 调用判题服务
        question_service = get_question_service()

        # 如果是临时题目，使用 AI 判题（需要题目文本）
        if is_temp_question:
            # 构建临时的判题请求
            from Education.services.questionService import QuestionService
            judge_result = QuestionService.ai_judge_question_with_data(
                question_data=question_data,
                user_answer=answer,
                user_id=user_id or 'anonymous',
                source='agent_chat'
            )
        else:
            # 从数据库查询题目进行判题
            judge_bo = AiJudgeQuestionBo(
                user_id=user_id or 'anonymous',
                question_id=question_id,
                answer=answer,
                source='agent_chat'
            )
            judge_result = question_service.ai_judge_question(judge_bo)

        # 构建回复
        score = judge_result.get('score', 0)
        ai_result = judge_result.get('ai_result', '')

        if score >= 0.8:
            response_text = f"太棒了！您的答案是正确的！\n\n{ai_result}"
        elif score >= 0.5:
            response_text = f"您的答案部分正确，得分率{score * 100:.0f}%。\n\n{ai_result}"
        else:
            response_text = f"您的答案有误，得分率{score * 100:.0f}%。\n\n{ai_result}"

        return {
            'intent': 'judge_answer',
            'answer': response_text,
            'data': judge_result
        }

    @staticmethod
    def _extract_answer_from_input(user_input: str) -> Optional[str]:
        """
        从用户输入中提取答案（处理简短回答）

        支持格式：
        - "我选 A" / "我选 AB" / "选 A" -> "A" / "AB"
        - "答案是 A" / "答案：A" -> "A"
        - "应该是 A" / "我觉得是 B" -> "A" / "B"
        - "对" / "正确" / "是的" -> "true"
        - "错" / "错误" / "不对" -> "false"

        Args:
            user_input: 用户输入

        Returns:
            提取的答案，如果无法提取则返回 None
        """
        import re

        user_input = user_input.strip()

        # 处理判断题
        if user_input in ['对', '正确', '是的', '没错', 'true', 'True', 'T']:
            return 'true'
        if user_input in ['错', '错误', '不对', 'false', 'False', 'F']:
            return 'false'

        # 匹配"我选 X"、"选 X"、"答案是 X"等格式
        patterns = [
            r'我选 [：:\s]*([A-F0-9]+)',      # 我选 A / 我选:A / 我选 AB
            r'选 [：:\s]*([A-F0-9]+)',        # 选 A / 选：B
            r'答案是 [：:\s]*([A-F0-9]+)',    # 答案是 A / 答案是：AB
            r'答案 [：:\s]*([A-F0-9]+)',      # 答案 A / 答案：B
            r'应该是 [：:\s]*([A-F0-9]+)',    # 应该是 A
            r'我觉得 [是]*[：:\s]*([A-F0-9]+)',  # 我觉得是 A / 我觉得 A
        ]

        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        # 如果用户输入很短（1-3 个字符），可能是直接的答案
        if 1 <= len(user_input) <= 3 and user_input.upper() in ['A', 'B', 'C', 'D', 'E', 'F', 'TRUE', 'FALSE', '对', '错']:
            return user_input.upper()

        return None

    async def handle_explain_question(
        self,
        user_input: str,
        intent_result: IntentRecognitionResult,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> dict:
        """
        处理题目解析意图
        """
        params = intent_result.params
        question_id = params.get('question_id')
        question_text = params.get('question_text')

        # 获取题目信息
        question = None
        if question_id:
            question = QuestionPo.get_by_id(question_id)
        elif question_text:
            # 如果没有题目 ID，尝试用文本生成解析
            return await self._explain_text_question(question_text, user_input)

        if not question:
            return {
                'intent': 'explain_question',
                'answer': "请提供要解析的题目 ID 或题目文本。",
                'data': None
            }

        # 构建解析 prompt
        system_prompt = EXPLAIN_QUESTION_SYSTEM_PROMPT
        user_prompt = f"""请解析以下题目：

题目：{question.question_text}
答案：{question.answer}
解析：{question.analysis or '请提供解析'}
解题步骤：{question.solution_steps or '请提供解题步骤'}
"""

        messages = [
            SystemMessages(prompt=system_prompt),
            UserMessages(prompt=user_prompt)
        ]

        llm = get_default_qwen_llm()
        response = llm.chat(messages)

        return {
            'intent': 'explain_question',
            'answer': response,
            'data': question.mini_dict if hasattr(question, 'mini_dict') else None
        }

    async def _explain_text_question(
        self,
        question_text: str,
        user_input: str
    ) -> dict:
        """
        解析纯文本题目
        """
        system_prompt = EXPLAIN_QUESTION_SYSTEM_PROMPT
        user_prompt = f"""请解析以下题目：

题目：{question_text}

用户问题：{user_input}
"""

        messages = [
            SystemMessages(prompt=system_prompt),
            UserMessages(prompt=user_prompt)
        ]

        llm = get_default_qwen_llm()
        response = llm.chat(messages)

        return {
            'intent': 'explain_question',
            'answer': response,
            'data': {'question_text': question_text}
        }

    async def handle_chat(
        self,
        user_input: str,
        intent_result: IntentRecognitionResult,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> dict:
        """
        处理聊天意图
        """
        # 获取记忆上下文
        context = MemoryV1Service.get_simple_memory(
            question=user_input,
            user_id=user_id,
            session_id=session_id
        )

        # 构建对话 messages
        messages = context + [UserMessages(prompt=user_input)]

        llm = get_default_qwen_llm()
        response = llm.chat(messages)

        return {
            'intent': 'chat',
            'answer': response,
            'data': None
        }

    async def handle_recommend_questions(
        self,
        user_input: str,
        intent_result: IntentRecognitionResult,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> dict:
        """
        处理推荐题目意图
        """
        params = intent_result.params
        subject = params.get('subject')
        weak_points = params.get('weak_points')

        # 根据薄弱知识点推荐题目
        # TODO: 实现更智能的推荐逻辑
        if subject:
            questions = QuestionPo.get_random_question(subject=subject, num=3)
        else:
            questions = QuestionPo.get_random_question(num=3)

        if not questions:
            questions = []
        elif not isinstance(questions, list):
            questions = [questions]

        question_list = [q.mini_dict for q in questions] if questions else []

        # 构建推荐理由
        reason = "根据您的学习情况"
        if weak_points:
            reason += f"，特别是{weak_points}这个知识点"
        reason += "，我为您推荐了以下练习题："

        answer = f"{reason}\n\n"
        for i, q in enumerate(question_list, 1):
            answer += f"{i}. {q.get('question_text', '')[:100]}...\n"

        return {
            'intent': 'recommend_questions',
            'answer': answer,
            'data': {
                'questions': question_list,
                'weak_points': weak_points,
                'recommendation_reason': reason
            }
        }

    async def handle_learning_progress(
        self,
        user_input: str,
        intent_result: IntentRecognitionResult,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> dict:
        """
        处理学习进度查询意图
        """
        params = intent_result.params
        subject = params.get('subject')
        time_range = params.get('time_range', '全部')

        # TODO: 实现学习进度查询逻辑
        # 目前返回模拟数据

        progress_data = {
            'total_questions': 0,
            'correct_rate': 0,
            'subject_stats': [],
            'recent_performance': '暂无数据',
            'improvement_suggestions': '请先完成一些题目，以便我为您分析学习进度。'
        }

        answer = "学习进度查询功能开发中，敬请期待！"

        return {
            'intent': 'learning_progress',
            'answer': answer,
            'data': progress_data
        }


# 全局服务实例
agent_chat_service = AgentChatService()


def get_agent_chat_service():
    """获取 Agent 聊天服务实例"""
    return agent_chat_service
