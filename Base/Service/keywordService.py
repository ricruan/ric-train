import logging

from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Client.jiebaClient import jieba_client
from Base.Models.BaseKeywordModel import BaseKeywordModel
from Base.Models.VdbKeyword import VDBLLMKeyword
from Base.Models.VdbLLMConversation import VdbLLMConversation

logger = logging.getLogger(__name__)


def register_keyword_into_jieba():
    """
    将关键词注册到 jieba 中
    """
    try:
        res = BaseKeywordModel.get_all_active()
        for i in res:
            jieba_client.add_word(i.keyword_name)
            logger.debug(f"已向jieba词典中加入关键字{i.keyword_name}")
    except Exception as e:
        logger.error(f"关键词注册到jieba中 失败：{str(e)}")


def keyword_replace_question(nl: str):
    """
    自然语言中的命名实体替换
    - jieba 分词
    - 查询数据库中的关键词
    - 查询 vdb 中的关键词
    - 替换
    """
    cut_result = jieba_client.cut(nl)
    print(cut_result)
    keywords_db = BaseKeywordModel.get_all_active()
    # keywords_vdb = VDBLLMKeyword.get_similarity_keywords(' '.join(cut_result))

    db_target_keywords = [i for i in keywords_db if i.keyword_name in cut_result]
    # vdb_target_keywords = [i for i in keywords_vdb if i.get('keyword_name') in cut_result]

    # 暂时忽略VDB，
    for i in db_target_keywords:
        nl = nl.replace(i.keyword_name, i.keyword_synonyms)

    return nl


def data_migration():
    """
    数据迁移 from db 2 vdb
    """
    res = BaseKeywordModel.get_all_active()
    for i in res:
        embedding = [0.1] * 1024
        if i.semantic_desc:
            embedding = get_default_qwen_llm().embedding(i.keyword_name)
        VDBLLMKeyword(keyword_name=i.keyword_name,
                      db_id=str(i.id),
                      keyword_code=i.keyword_code,
                      keyword_desc=i.keyword_desc or '',
                      semantic_desc=i.semantic_desc or '',
                      keyword_synonyms=i.keyword_synonyms or '',
                      embedding=embedding
                      ).save()


if __name__ == '__main__':
    register_keyword_into_jieba()
    print(keyword_replace_question("沃林数字的刘硕是谁"))
