import json
import time
from functools import wraps
from typing import Optional, Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from Base.Ai.base import UserMessages
from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.llms.qwenLlm import QwenLlm
from Base.Models.BaseLLMConversationModel import BaseLLMConversationModel
from Base.Models.BaseLLMSession import BaseLLMSession
from Base.RicUtils.httpUtils import HttpResponse
from Base.Service.memoryV1Service import MemoryV1Service
from Base.Service.aiService import AiService, AuditingTextError
from Base.Service.keywordService import keyword_replace_question
from Base.Service.llmConversationService import save_conversation_from_db_2_vdb, save_conversation_from_db_2_vdb_only_data


def persist_conversation(auto_save_vdb: bool = True, is_rewriting: bool = True, is_auditing: bool = True):
    """
    装饰器：自动持久化对话记录

    Args:
        auto_save_vdb: 是否自动保存到向量数据库
        is_rewriting: 是否问题改写
        is_auditing: 是否文本校验
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取参数
            params = kwargs.get('params') or (args[0] if args else None)
            if not params:
                return func(*args, **kwargs)

            logger = __import__('logging').getLogger(__name__)

            # 记录开始时间
            start_time = time.time()
            conversation = params.to_log_instance()

            try:
                # 以下所有装饰器内部逻辑都包裹在 try-except 中，确保不影响被装饰函数
                session = BaseLLMSession.get_user_last_session(params.user_id, params.session_id)
                conversation.session_id = session.session_uuid
                llm = QwenLlm()
                conversation.ai_model = llm.model_name
                conversation.source = "base_chat_api"

                question = keyword_replace_question(params.question)
                rewrite_question = ''

                # 文本审核
                if is_auditing:
                    auditing_dict = AiService.auditing_text(question)
                    if auditing_dict.get('status') == 0:
                        conversation.error_msg = auditing_dict.get('reason')
                        raise AuditingTextError

                if is_rewriting:
                    rewrite_question = AiService.rewrite_question(question=question, user_id=params.user_id,
                                                                  session_id=params.session_id)
                    conversation.rewrite_question = rewrite_question
                context = MemoryV1Service.get_simple_memory(
                    question=rewrite_question or question,
                    user_id=params.user_id,
                    session_id=session.session_uuid or params.session_id
                )
                kwargs.get('params').messages = context + [UserMessages(prompt=question)]
                conversation.context = str(context)

                try:
                    # 执行原始函数
                    result = func(*args, **kwargs)

                    # 如果是流式响应，需要特殊处理
                    if params.is_stream:
                        # 包装流式响应生成器
                        original_generator = result.body_iterator

                        # 在生成器外部准备数据收集容器
                        # 使用独立变量而非闭包引用 conversation，避免 pickle 问题
                        stream_data_collector = {
                            'reasoning_parts': [],
                            'answer_parts': [],
                            'completed': False,
                            'error': None
                        }

                        async def wrapped_generator():
                            try:
                                # 先完成流式输出
                                async for chunk in original_generator:
                                    # 根据 chunk 类型进行处理
                                    if isinstance(chunk, dict):
                                        # 如果是字典类型（Qwen thinking 模式）
                                        chunk_type = chunk.get('type', 'content')
                                        chunk_content = chunk.get('content', '')

                                        # 分别收集不同类型的內容
                                        if chunk_type == 'reasoning':
                                            stream_data_collector['reasoning_parts'].append(chunk_content)
                                        else:  # 'content' 或其他类型
                                            stream_data_collector['answer_parts'].append(chunk_content)

                                        sse_data = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                                        yield sse_data.encode("utf-8")  # 必须是 bytes

                                    elif isinstance(chunk, str):
                                        # 如果是字符串类型（普通流式输出）
                                        stream_data_collector['answer_parts'].append(chunk)
                                        sse_data = f"data: {chunk}\n\n"
                                        yield sse_data.encode("utf-8")

                                    elif isinstance(chunk, bytes):
                                        # 如果已经是 bytes 类型
                                        yield chunk
                                    else:
                                        # 其他类型转换为字符串处理
                                        chunk_str = str(chunk)
                                        stream_data_collector['answer_parts'].append(chunk_str)
                                        sse_data = f"data: {chunk_str}\n\n"
                                        yield sse_data.encode("utf-8")

                                # 流式输出完成，进行持久化（使用纯数据，避免引用 conversation 对象）
                                stream_data_collector['completed'] = True
                                try:
                                    # 准备持久化数据（纯数据字典）
                                    duration_ms = int((time.time() - start_time) * 1000)
                                    if params.is_thinking:
                                        answer = json.dumps({
                                            'reasoning': ''.join(stream_data_collector['reasoning_parts']),
                                            'content': ''.join(stream_data_collector['answer_parts'])
                                        }, ensure_ascii=False, separators=(',', ':'))
                                    else:
                                        answer = ''.join(stream_data_collector['answer_parts'])

                                    # 更新 conversation 对象（在主线程中）
                                    conversation.answer = answer
                                    conversation.duration_ms = duration_ms
                                    conversation.save()

                                    # 保存到 VDB（使用纯数据字典）
                                    if auto_save_vdb:
                                        save_conversation_from_db_2_vdb_only_data({
                                            'id': conversation.id,
                                            'session_id': conversation.session_id,
                                            'user_id': conversation.user_id,
                                            'question': conversation.question,
                                            'rewrite_question': conversation.rewrite_question,
                                            'answer': conversation.answer
                                        })
                                except Exception as save_error:
                                    logger.error(f"流式结束后保存对话记录失败：{str(save_error)}")
                                    # 持久化异常不影响流式输出

                            except Exception as e:
                                stream_data_collector['error'] = str(e)
                                logger.error(f"流式处理异常：{str(e)}")
                                raise

                        # 在生成器执行完成后处理持久化
                        # 注意：由于流式输出的特殊性，持久化需要在生成器完成后进行
                        # 我们创建一个包装函数来处理这个问题
                        result.body_iterator = wrapped_generator()

                        # 流式输出的持久化在生成器完成后进行
                        # 由于无法直接等待异步生成器，我们在返回后通过后台任务处理
                        # 这里先返回结果，持久化在生成器内部完成后处理
                        return result
                    else:
                        result_str = result.data if isinstance(result, HttpResponse) else result
                        # 非流式响应直接保存
                        conversation.answer = result_str if isinstance(result_str, str) else str(result_str)
                        conversation.duration_ms = int((time.time() - start_time) * 1000)
                        conversation.save()
                        if auto_save_vdb:
                            # 传递纯数据字典，避免 pickle 错误
                            save_conversation_from_db_2_vdb_only_data({
                                'id': conversation.id,
                                'session_id': conversation.session_id,
                                'user_id': conversation.user_id,
                                'question': conversation.question,
                                'rewrite_question': conversation.rewrite_question,
                                'answer': conversation.answer
                            })
                        return result

                except Exception as e:
                    # 异常时也记录错误信息
                    conversation.status = 'failed'
                    conversation.error_msg = str(e)
                    conversation.duration_ms = int((time.time() - start_time) * 1000)
                    conversation.save()
                    raise

            except AuditingTextError:
                conversation.status = 'failed'
                conversation.duration_ms = int((time.time() - start_time) * 1000)
                conversation.save()
                return HttpResponse.error(
                    msg='根据中华人民共和国《生成式人工智能服务管理暂行办法》,您的问题涉嫌包含敏感信息，我将无法处理您的请求')
            except Exception as e:
                # 捕获装饰器内部所有其他异常，记录日志但不影响被装饰函数
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"装饰器内部异常：{str(e)}\n{error_traceback}")
                try:
                    conversation.status = 'failed'
                    conversation.error_msg = f"装饰器内部错误：{str(e)}"
                    conversation.duration_ms = int((time.time() - start_time) * 1000)
                    conversation.save()
                except Exception as log_error:
                    logger.error(f"记录装饰器异常失败：{str(log_error)}")

                # 返回被装饰函数的原始结果，不中断业务逻辑
                return func(*args, **kwargs)

        return wrapper

    return decorator


class ChatParams(BaseModel):
    question: str = Field(..., description="用户问题")
    user_id: Optional[str] = Field(None, description="用户标识")
    model_type: LLMTypeEnum = Field(LLMTypeEnum.QWEN, description="模型类型")
    session_id: Optional[str] = Field(None, description="会话标识")
    is_stream: bool = Field(False, description="是否流式输出")
    is_thinking: bool = Field(False, description="是否思考")
    is_online_search: bool = Field(False, description="是否在线搜索")
    invoke_params: Optional[dict] = Field({}, description="调用参数")
    messages: Optional[list] = Field(None, description="消息列表")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.is_thinking:
            self.is_stream = True
        if not self.messages:
            self.messages = [UserMessages(self.question)]

    def to_log_instance(self) -> BaseLLMConversationModel:
        return BaseLLMConversationModel(
            question=self.question,
            user_id=self.user_id,
            session_id=self.session_id,
            ai_model=self.model_type.value,
            stream_mode="1" if self.is_stream else "0"
        )


router = APIRouter()


@router.post("/chat-v1")
@persist_conversation(auto_save_vdb=True,is_auditing=False)
def chat(params: ChatParams):
    """
    对话接口
    - 支持流式输出（is_stream=True）
    - 支持思考模式（is_thinking=True）
    - 自动持久化会话记录到传统 DB 和 VDB（通过装饰器非侵入式实现）
    """
    llm = QwenLlm()
    full_messages = params.messages

    if params.is_stream:
        # 流式输出：启用思考模式和流式传输
        stream = llm.chat(
            messages=full_messages,
            enable_thinking=params.is_thinking,
            enable_search=params.is_online_search,
            stream=True,
            **params.invoke_params
        )
        return StreamingResponse(stream, media_type="text/event-stream")
    else:
        # 非流式输出
        result = llm.chat(messages=full_messages, enable_search=params.is_online_search, **params.invoke_params)
        return HttpResponse.ok(result)


def register_ai_chat_router(app):
    app.include_router(router)
