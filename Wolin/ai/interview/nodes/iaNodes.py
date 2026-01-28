import json

from Base.Ai.base import SystemMessages, UserMessages
from Base.Client import asr_client
from Base.RicUtils.audioFileUtils import AudioFileHandler
from Base.RicUtils.pdfUtils import extract_pdf_text
from Wolin.ai.interview.iaState import IAState, ResumeInfo
from Wolin.prompt.insertviewPrompt import ANALYSIS_START_PROMPT, RESUME_JSON_EXTRACT_PROMPT
from WorkFlow.base.baseState import BaseState
from WorkFlow.base.decorators import graph_node


@graph_node
def extract_resume(state: BaseState):
    resume_content = extract_pdf_text(state.resume_info.resume_path)
    resume_infos = state.default_model.chat([SystemMessages(RESUME_JSON_EXTRACT_PROMPT), UserMessages(resume_content)])
    resume_info_json = json.loads(resume_infos)
    state.resume_info = ResumeInfo(**resume_info_json)
    return state





@graph_node
def audio_handle(state: BaseState):
    handler = AudioFileHandler()
    # 将文件拆成碎片
    temp_file_list = handler.split_audio_with_overlap_ffmpeg(input_audio_path=state.asr_info.audio_path
                                                             , max_segment_duration=100
                                                             , overlap_duration=2
                                                             , output_format='wav')
    # 按顺序并发ASR处理
    ordered_results = asr_client.audio_2_text(temp_file_list)
    # 合并碎片文本
    combine_text = state.default_model.chat([SystemMessages(ANALYSIS_START_PROMPT), UserMessages(ordered_results)])

    pass


@graph_node
def get_report_paragraph1(state: BaseState):
    res = state.default_model.chat([SystemMessages(ANALYSIS_START_PROMPT), UserMessages(state.asr_info.audio_text)])
    state.report.report_paragraph1 = res


if __name__ == '__main__':
    state = IAState()
    state.resume_info.resume_path = r'C:\Users\11243\Desktop\李琳_个人简历.pdf'
    extract_resume(state)
    print(state.resume_info)
    print(1)
