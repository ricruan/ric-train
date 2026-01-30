import json
import logging
import os
import sys
import uuid

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
    INTERVIEW_EVALUATION_PROMPT, SELF_EVALUATION_PROMPT, ANALYSIS_END_PROMPT
from Wolin.service import get_email_service
from WorkFlow import BaseWorkFlow, load_node
from WorkFlow.base.decorators import graph_node

logger = logging.getLogger(__name__)

@graph_node
def extract_resume(state: IAState):
    """
    简历抽取节点
    :param state:
    :return:
    """
    if not state.resume_info.resume_path:
        return None
    resume_content = extract_pdf_text(state.resume_info.resume_path)
    resume_infos = default_qwen_llm.chat([SystemMessages(RESUME_JSON_EXTRACT_PROMPT), UserMessages(resume_content)])
    resume_info_json = json.loads(resume_infos)
    state.resume_info = ResumeInfo(**resume_info_json)
    return {'resume_info': state.resume_info}


@graph_node
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
    state.resume_info.resume_analysis = res
    updated_resume = state.resume_info.model_copy(
        update={"resume_analysis": res}
    )
    return {'resume_info': {"resume_analysis": res}}


@graph_node
def resume_handle(state: IAState):
    """
    简历处理
    :param state:
    :return:
    """
    extract_resume(state)
    resume_analysis(state)

@graph_node
def audio_handle(state: IAState):
    """
     音频处理节点 with cache
    :param state:
    :return:
    """
    # 音频文件转文本碎片
    ordered_results = audio_file_2_text_with_cache(state.asr_info.audio_path)

    combine_prompt = render(COMBINE_SLICE_PROMPT, {"resume_info": state.resume_info.model_dump()})

    @cache_with_params(key_template="get_combine_text:{str_hash_code}", expire=3000)
    def get_combine_text(str_hash_code: str):
        return default_qwen_llm.chat([SystemMessages(combine_prompt), UserMessages(str(ordered_results))])

    # 合并碎片文本
    combine_text = get_combine_text(str_hash_code=short_unique_hash(str(ordered_results)))
    state.asr_info.audio_text = combine_text
    updated_asr = state.asr_info.model_copy(
        update={"audio_text": combine_text}
    )
    return {'asr_info': updated_asr}


@graph_node
def get_report_paragraph1(state: IAState):
    """
    获取报告的第一段落
    :param state:
    :return:
    """
    res = default_qwen_llm.chat([SystemMessages(ANALYSIS_START_PROMPT), UserMessages(state.asr_info.audio_text)])
    state.report.analysis_start = res
    updated_report = state.report.model_copy(
        update={"analysis_start": res}
    )
    return {"report": {"analysis_start": res}}


@graph_node
def get_report_table_data_json(state: IAState):
    """
    获取报告的表格数据json
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
def get_qa_pair(state: IAState):
    """
    获取面试中的技术问答对
    :param state:
    :return:
    """
    res = default_qwen_llm.chat([SystemMessages(CORE_QA_EXTRACT_PROMPT), UserMessages(state.asr_info.audio_text)])
    res = json.loads(res)
    updated_asr = state.asr_info.model_copy(
        update={"qa_pairs": res}
    )
    return {"asr_info": {"qa_pairs": res}}


@graph_node
def qa_pairs_analysis(state: IAState):
    """
    问答对分析
    :param state:
    :return:
    """
    res = default_qwen_llm.chat([SystemMessages(CORE_QA_ANALYSIS_PROMPT), UserMessages(str(state.asr_info.qa_pairs))],timeout=240.0)
    return {"report": {"qa_analysis": json.loads(res)}}


@graph_node
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
def self_evaluation(state: IAState):
    """
    求职者评价
    :param state:
    :return:
    """
    system_prompt = render(SELF_EVALUATION_PROMPT, {"analysis_start": state.report.analysis_start})
    res = default_qwen_llm.chat([SystemMessages(system_prompt), UserMessages(state.asr_info.audio_text)])
    updated_report = state.report.model_copy(
        update={"self_evaluation": res}
    )
    return {"report": {"self_evaluation": res}}


@graph_node
def analysis_end(state: IAState):
    """
    分析报告最后一段
    :param state:
    :return:
    """
    system_prompt = render(ANALYSIS_END_PROMPT, {"analysis_start": state.report.analysis_start})
    res = default_qwen_llm.chat([SystemMessages(system_prompt), UserMessages(state.asr_info.audio_text)])
    updated_report = state.report.model_copy(
        update={"analysis_end": res}
    )
    return {"report": {"analysis_end": res}}


@graph_node
def generate_report(state: IAState):
    """
    生成报告
    :param state:
    :return:
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "../../../static/template.docx")
    logger.debug("======报告上下文参数==========")
    logger.debug(f'报告的参数上下文dict: {state.context_params}')
    output_path = generate_doc_with_jinja(template_path, state.context_params)
    logger.info(f"面试报告临时存储位置：\n {output_path}")
    default_minio_client.upload_file(bucket_name="interview-report",
                              object_name=state.minio_path,
                              file_path=output_path)

    uuid_str = str(uuid.uuid4())
    get_email_service().send_emails_4_ia(
        user_name=state.api_params.user_name,
        ia_id=uuid_str,
        report_path=state.minio_path,
        user_email=['2366692214@qq.com',state.api_params.receive_email]
    )



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
        node_list = [['extract_resume', 'audio_handle'],
                     ['get_report_paragraph1', 'get_qa_pair', 'resume_analysis'],
                     ['analysis_end', 'self_evaluation', 'ai_evaluation', 'qa_pairs_analysis',
                      'get_report_table_data_json'],'generate_report']
        wf = BaseWorkFlow(node_list=node_list, state_schema=IAState)
        wf.invoke(input_data=_state)
        print(1)


    test_full_process()
