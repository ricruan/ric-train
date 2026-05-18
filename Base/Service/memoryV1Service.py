import logging

from Base.Models.BaseLLMConversationModel import BaseLLMConversationModel
from Base.Models.BaseLLMSession import BaseLLMSession
from Base.Models.VdbLLMConversation import VdbLLMConversation

logger = logging.getLogger(__name__)


class MemoryV1Service:

    @staticmethod
    def get_simple_memory(question: str, user_id: str = None, session_id: str = None):
        """
        获取最简单的记忆
        记忆组成：
        - 【即时记忆】记录最近N轮对话内容，聚焦当前会话脉络（“刚刚在聊什么”）。
        - 【记忆锚点】检索与当前话题高度相关的历史对话（相似度高于设定阈值），用于精准关联（“之前聊过什么相同话题”）。
        - 【模糊回忆】提取会话的历史摘要信息，唤起整体讨论主题的轮廓（“以前讨论过哪些主要方向”）。
        """
        # from db
        history = BaseLLMConversationModel.get_last_n_turns_context(user_id, session_id, 3)
        db_ids = [str(item.id) for item in history if isinstance(item, BaseLLMConversationModel)]
        history = BaseLLMConversationModel.db_res_2_messages(history)
        # from vdb
        similar_items = VdbLLMConversation.get_n_high_similarity_item(question, user_id, session_id, n=10)
        logger.debug(f"【Simple Memory】DB近N轮已使用的 db_id: {db_ids}")
        logger.debug(f"【Simple Memory】VDB召回的 db_id: {[item.get('db_id') for item in similar_items]}")
        # 去重
        similar_items = [i for i in similar_items if i.get('db_id') not in db_ids]
        # todo:  相似度最低限制 做成 系统参数
        similar_items = [i for i in similar_items if i.get('distance') > 0.5]
        logger.debug(f"【Simple Memory】相似度筛选后的 db_id: {[item.get('db_id') for item in similar_items]}")
        similar_items = VdbLLMConversation.vdb_res_2_messages(similar_items)

        # from session
        session = []
        last_session = BaseLLMSession.get_user_last_session(user_id, session_id)
        if last_session:
            session = last_session.to_messages()


        return session + similar_items + history


if __name__ == '__main__':
    service = MemoryV1Service()
    context1 = service.get_simple_memory(question="你好", user_id="string", session_id="string")
    # context2 = service.get_n_high_similarity_item(question="五 加 六 等于几", n=5)
    # print(context1)
    # print(context2)
    for i1 in context1:
        print(i1)
