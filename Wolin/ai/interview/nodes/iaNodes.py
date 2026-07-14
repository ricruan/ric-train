import json
import logging
import os
import sys
import uuid
from datetime import datetime

from Base import default_qwen_llm
from Base.Ai.base import SystemMessages, UserMessages
from Base.Client.minioClient import default_minio_client
from Base.RicUtils.dataUtils import short_unique_hash
from Base.RicUtils.docUtils import generate_doc_with_jinja
from Base.RicUtils.pdfUtils import extract_pdf_text
from Base.RicUtils.redisUtils import cache_with_params
from Base.Service.asrService import audio_file_2_text_with_cache
from Wolin.ai.interview.iaState import IAState, ResumeInfo
from Wolin.prompt.insertviewPrompt import ANALYSIS_START_PROMPT, RESUME_JSON_EXTRACT_PROMPT, COMBINE_SLICE_PROMPT, \
    render, REPORT_PROMPT, CORE_QA_EXTRACT_PROMPT, test, CORE_QA_ANALYSIS_PROMPT, RESUME_ANALYSIS_PROMPT, \
    INTERVIEW_EVALUATION_PROMPT, SELF_EVALUATION_PROMPT, ANALYSIS_END_PROMPT, COMBINE_SLICE_PROMPT_V2
from Wolin.service import get_email_service
from Wolin.service.interviewRecordService import get_interview_record_service
from WorkFlow import BaseWorkFlow, load_node
from WorkFlow.base.decorators import graph_node
from Wolin.ai.interview.nodes.iaDecorator import capture_node_error

logger = logging.getLogger(__name__)

# 全局变量：记录 UUID（在工作流执行过程中传递）
_current_record_uuid = None


@graph_node
def init_record(state: IAState):
    """
    初始化持久化记录节点（工作流第一个节点）
    :param state:
    :return:
    """
    global _current_record_uuid
    try:
        record = get_interview_record_service().create_initial_record(state)
        if record:
            _current_record_uuid = record.record_uuid
            # 将 record_uuid 存入 state，供后续节点使用
            state.record_uuid = _current_record_uuid
            logger.info(f"初始化记录成功，uuid={_current_record_uuid}")
        else:
            logger.warning("初始化记录失败，继续执行工作流")
    except Exception as e:
        logger.error(f"init_record 节点失败：{e}", exc_info=True)
    return {}


@graph_node
@capture_node_error()
def extract_resume(state: IAState):
    """
    简历抽取节点
    :param state:
    :return:
    """
    if not state.resume_info.resume_path:
        return None
    try:
        actual_name = default_minio_client.upload_file(bucket_name="resumes",
                                         object_name=state.resume_path + os.path.basename(state.resume_info.resume_path),
                                         file_path=state.resume_info.resume_path)
        if actual_name:
            state.resume_minio_path = actual_name
    except Exception as e:
        logger.error(f"{state.api_params.user_name} 简历 文件上传 MinIO 时发生异常：{e}")
    resume_content = extract_pdf_text(state.resume_info.resume_path)
    resume_infos = default_qwen_llm.chat([SystemMessages(RESUME_JSON_EXTRACT_PROMPT), UserMessages(resume_content)])
    resume_info_json = json.loads(resume_infos)
    state.resume_info = ResumeInfo(**resume_info_json, resume_path=state.resume_info.resume_path)
    return {'resume_info': state.resume_info, 'resume_minio_path': state.resume_minio_path}


@graph_node
@capture_node_error()
def resume_analysis(state: IAState):
    """
    简历分析
    :param state:
    :return:
    """
    if not state.resume_info.resume_path:
        return None
    res = default_qwen_llm.chat(
        [SystemMessages(RESUME_ANALYSIS_PROMPT), UserMessages(str(state.resume_info.model_dump()))])
    return {'report': {"resume_analysis": res}}


@graph_node
@capture_node_error()
def audio_handle(state: IAState):
    """
     音频处理节点 with cache
    :param state:
    :return:
    """
    try:
        actual_name = default_minio_client.upload_file(bucket_name="audios",
                                         object_name=state.audio_path,
                                         file_path=state.asr_info.audio_path)
        if actual_name:
            state.audio_minio_path = actual_name
    except Exception as e:
        logger.error(f"{state.api_params.user_name}Audio 文件上传 MinIO 时发生异常：{e}")
    # 音频文件转文本碎片
    ordered_results = audio_file_2_text_with_cache(state.asr_info.audio_path)

    combine_prompt = render(COMBINE_SLICE_PROMPT, {"resume_info": state.resume_info.model_dump()})

    origin_combine_prompt = render(COMBINE_SLICE_PROMPT_V2, {"resume_info": state.resume_info.model_dump()})

    @cache_with_params(key_template="get_combine_text:{str_hash_code}", expire=3000)
    def get_combine_text(str_hash_code: str):
        return default_qwen_llm.chat([SystemMessages(combine_prompt), UserMessages(str(ordered_results))])

    @cache_with_params(key_template="get_combine_text:{str_hash_code}", expire=3000)
    def get_origin_combine_text(str_hash_code: str):
        return default_qwen_llm.chat([SystemMessages(origin_combine_prompt), UserMessages(str(ordered_results))])

    # 合并碎片文本
    combine_text = get_combine_text(str_hash_code=short_unique_hash(str(ordered_results)))

    origin_combine_text = get_origin_combine_text(str_hash_code=short_unique_hash(str(ordered_results)))

    try:
        actual_name = default_minio_client.str_list_2_minio(str_list=combine_text,
                                              bucket_name='audio-text',
                                              object_name=state.audio_text_path)
        if actual_name:
            state.audio_text_minio_path = actual_name
    except Exception as e:
        logger.error(f"{state.api_params.user_name}Audio-Text 文件上传 MinIO 时发生异常：{e}")

    try:
        actual_name = default_minio_client.str_list_2_minio(str_list=origin_combine_text,
                                              bucket_name='audio-text-origin',
                                              object_name=state.audio_text_path.replace('.txt', '_origin.txt'))
        if actual_name:
            state.audio_text_origin_minio_path = actual_name
    except Exception as e:
        logger.error(f"{state.api_params.user_name}Audio-Text-Origin 文件上传 MinIO 时发生异常：{e}")

    state.asr_info.audio_text = combine_text
    return {'asr_info': {"audio_text": combine_text}, 'audio_minio_path': state.audio_minio_path, 'audio_text_minio_path': state.audio_text_minio_path, 'audio_text_origin_minio_path': state.audio_text_origin_minio_path}


@graph_node
@capture_node_error()
def get_report_paragraph1(state: IAState):
    """
    获取报告的第一段落
    :param state:
    :return:
    """
    res = default_qwen_llm.chat([SystemMessages(ANALYSIS_START_PROMPT), UserMessages(state.asr_info.audio_text)])
    state.report.analysis_start = res
    return {"report": {"analysis_start": res}}


@graph_node
@capture_node_error()
def get_report_table_data_json(state: IAState):
    """
    获取报告的表格数据 json
    :param state:
    :return:
    """
    res = default_qwen_llm.chat([SystemMessages(REPORT_PROMPT), UserMessages(state.asr_info.audio_text)])
    res_json = json.loads(res)
    updated_report = state.report.model_copy(
        update={"interview_json": res_json}
    )
    return {"report": updated_report}


@graph_node
@capture_node_error()
def get_qa_pair(state: IAState):
    """
    获取面试中的技术问答对
    :param state:
    :return:
    """
    res = default_qwen_llm.chat([SystemMessages(CORE_QA_EXTRACT_PROMPT), UserMessages(state.asr_info.audio_text)])
    res = json.loads(res)
    return {"asr_info": {"qa_pairs": res, "audio_text": state.asr_info.audio_text}}


@graph_node
@capture_node_error()
def qa_pairs_analysis(state: IAState):
    """
    问答对分析
    :param state:
    :return:
    """
    res = default_qwen_llm.chat([SystemMessages(CORE_QA_ANALYSIS_PROMPT), UserMessages(str(state.asr_info.qa_pairs))],
                                timeout=240.0)
    return {"report": {"qa_analysis": json.loads(res)}}


@graph_node
@capture_node_error()
def ai_evaluation(state: IAState):
    """
    面试评价
    :param state:
    :return:
    """
    system_prompt = render(INTERVIEW_EVALUATION_PROMPT, {"analysis_start": state.report.analysis_start})
    res = default_qwen_llm.chat([SystemMessages(system_prompt), UserMessages(state.asr_info.audio_text)])
    return {"report": {"interview_evaluation": res}}


@graph_node
@capture_node_error()
def self_evaluation(state: IAState):
    """
    求职者评价
    :param state:
    :return:
    """
    system_prompt = render(SELF_EVALUATION_PROMPT, {"analysis_start": state.report.analysis_start})
    res = default_qwen_llm.chat([SystemMessages(system_prompt), UserMessages(state.asr_info.audio_text)])
    return {"report": {"self_evaluation": res}}


@graph_node
@capture_node_error()
def analysis_end(state: IAState):
    """
    分析报告最后一段
    :param state:
    :return:
    """
    system_prompt = render(ANALYSIS_END_PROMPT, {"analysis_start": state.report.analysis_start})
    res = default_qwen_llm.chat([SystemMessages(system_prompt), UserMessages(state.asr_info.audio_text)])
    return {"report": {"analysis_end": res}}


@graph_node
@capture_node_error()
def generate_report(state: IAState):
    """
    生成报告
    :param state:
    :return:
    """
    global _current_record_uuid
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "../../../static/template.docx")
    logger.debug("======报告上下文参数==========")
    logger.debug(f'报告的参数上下文 dict: {state.context_params}')

    output_path = generate_doc_with_jinja(template_path, state.context_params)
    logger.info(f"面试报告临时存储位置：\n {output_path}")

    try:
        actual_name = default_minio_client.upload_file(bucket_name="interview-report",
                                         object_name=state.minio_path,
                                         file_path=output_path)
        if actual_name:
            state.report_minio_path = actual_name
    except Exception as e:
        logger.error(f"{state.api_params.user_name}报告 MinIO 存储失败：{e}")

    try:
        uuid_str = str(uuid.uuid4())
        get_email_service().send_emails_4_ia(
            user_name=state.api_params.user_name,
            ia_id=uuid_str,
            report_path=output_path,
            user_email=['2366692214@qq.com', state.api_params.receive_email]
        )
    except Exception as e:
        logger.error(f"报告邮件发送失败：{e}")

    if output_path and os.path.exists(output_path):
        os.unlink(output_path)
    return {'report_minio_path': getattr(state, 'report_minio_path', None)}


@graph_node
def persist_record(state: IAState):
    """
    持久化记录节点（工作流最后一个节点，无论成功失败都执行）
    :param state:
    :return:
    """
    # 优先使用 state 中传递的 record_uuid，其次使用全局变量
    record_uuid = getattr(state, 'record_uuid', None) or _current_record_uuid

    try:
        # 保存最终记录
        success = get_interview_record_service().save_final_record(state, record_uuid)
        if success:
            logger.info(f"persist_record 节点执行成功，uuid={record_uuid}")
        else:
            logger.warning(f"persist_record 节点执行失败")
    except Exception as e:
        logger.error(f"persist_record 节点异常：{e}", exc_info=True)
        # 即使持久化失败，也尝试用备用方式保存
        get_interview_record_service().save_with_error(state, str(e), 'persist_record')
    return {}


def get_ia_node_list():
    """
    工作流 节点列表
    :return:
    """
    return [
        'init_record',  # 新增：初始化记录
        'extract_resume',
        'resume_analysis',
        'audio_handle',
        ['get_report_paragraph1', 'get_qa_pair'],
        ['analysis_end', 'self_evaluation', 'ai_evaluation', 'qa_pairs_analysis',
         'get_report_table_data_json'],
        'generate_report',
        'persist_record'  # 新增：持久化记录
    ]


def get_workflow():
    """
    工作流
    :return:
    """
    return BaseWorkFlow(node_list=get_ia_node_list(), state_schema=IAState)


if __name__ == '__main__':
    def test_extract_resume():
        _state = IAState()
        _state.resume_info.resume_path = r'C:\Users\11243\Desktop\李琳_个人简历.pdf'
        extract_resume(_state)
        print(1)


    def test_audio_handle():
        _state = IAState()
        _state.asr_info.audio_path = r'C:\Users\11243\Desktop\黄立强南方电网.m4a'
        audio_handle(_state)
        print(1)


    def test_get_qa_pair():
        _state = IAState()
        _state.asr_info.audio_text = test
        get_qa_pair(_state)
        print(1)


    def test_full_process():
        load_node(sys.modules[__name__])
        _state = IAState()
        _state.ric_id = '1111'
        _state.resume_info.resume_path = r'C:\Users\11243\Desktop\黄简历.pdf'
        _state.asr_info.audio_path = r'C:\Users\11243\Desktop\黄立强南方电网.m4a'
        _state.api_params.user_name = '黄立强'
        _state.api_params.receive_email = '2366692214@qq.com'
        _state.api_params.company_name = '南方电网'
        node_list = get_ia_node_list()
        wf = BaseWorkFlow(node_list=node_list, state_schema=IAState)
        wf.invoke(input_data=_state)
        print(1)


    test_full_process()
