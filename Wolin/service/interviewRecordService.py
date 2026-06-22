import json
import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from Wolin.ai.interview.iaState import IAState

from Wolin.models.po.interviewRecordPo import InterviewRecordPo

logger = logging.getLogger(__name__)


class InterviewRecordService:
    """
    面试记录持久化服务

    确保无论工作流成功或失败，都有记录留存
    """

    @staticmethod
    def create_initial_record(state: 'IAState') -> Optional[InterviewRecordPo]:
        """
        创建工作流初始记录（在开始执行前调用）

        Args:
            state: IAState 实例

        Returns:
            创建的 InterviewRecordPo 实例，失败返回 None
        """
        try:
            record = InterviewRecordPo(
                user_name=getattr(state.api_params, 'user_name', '') or '',
                user_email=getattr(state.api_params, 'receive_email', None),
                company_name=getattr(state.api_params, 'company_name', None),
                status='processing',
            )

            # 如果有 ric_id，可以使用它关联（这里用 record_uuid）
            if state.ric_id:
                logger.info(f"创建工作流记录，ric_id={state.ric_id}, user={record.user_name}")
            else:
                logger.info(f"创建工作流记录，user={record.user_name}")

            record_id = record.save()
            if record_id > 0:
                logger.info(f"初始记录创建成功，id={record_id}")
                return record
            else:
                logger.error(f"初始记录创建失败，save 返回 id={record_id}")
                return None

        except Exception as e:
            logger.error(f"create_initial_record 失败：{e}", exc_info=True)
            return None

    @staticmethod
    def update_record_from_state(state: 'IAState', record_uuid: str = None,
                                  status: str = None, error_msg: str = None) -> bool:
        """
        从 state 更新记录

        Args:
            state: IAState 实例
            record_uuid: 记录 UUID（如果为 None，则使用 state 中传递的 record_uuid）
            status: 状态（processing/completed/failed）
            error_msg: 错误信息

        Returns:
            是否更新成功
        """
        try:
            # 1. 查找记录
            record = None
            if record_uuid:
                record = InterviewRecordPo.find_one_by(record_uuid=record_uuid)
                logger.info(f"根据 uuid 查找记录：{record_uuid}, 找到：{record is not None}, id={record.id if record else None}")

            if not record:
                # 按用户和公司查找最新处理中的记录
                record = InterviewRecordPo.find_one_by(
                    user_name=state.api_params.user_name,
                    company_name=state.api_params.company_name,
                    status='processing',
                    order_by='created_at',
                    order='DESC'
                )
                logger.info(f"根据 user_name+company 查找记录，找到：{record is not None}")

            if not record:
                logger.warning(f"未找到记录，无法更新")
                return False

            logger.info(f"开始更新记录 uuid={record.record_uuid}, id={record.id}")

            # 构建更新数据字典
            update_data = {}

            # 2. 更新 ASR 信息
            if state.asr_info:
                # 存储 MinIO 对象路径（不是本地临时路径）
                if getattr(state, 'audio_path', None):
                    update_data['audio_file_path'] = state.audio_path
                if state.asr_info.audio_text:
                    update_data['audio_text'] = state.asr_info.audio_text
                    logger.info(f"更新 audio_text，长度：{len(state.asr_info.audio_text)}")
                if getattr(state, 'audio_text_path', None):
                    update_data['audio_text_path'] = state.audio_text_path
                if getattr(state, 'audio_text_origin_path', None):
                    update_data['audio_text_origin_path'] = state.audio_text_origin_path
                if state.asr_info.qa_pairs:
                    update_data['qa_pairs'] = json.dumps(state.asr_info.qa_pairs, ensure_ascii=False)

            # 3. 更新简历信息
            if state.resume_info:
                resume_data = state.resume_info.model_dump(exclude_none=True)
                if resume_data:
                    update_data['resume_info'] = json.dumps(resume_data, ensure_ascii=False)
                # 存储 MinIO 对象路径（上传后 state.resume_path 返回实际路径）
                if getattr(state, 'resume_path', None):
                    update_data['resume_file_path'] = state.resume_path

            # 4. 更新报告信息
            if state.report:
                if state.report.analysis_start:
                    update_data['analysis_start'] = state.report.analysis_start
                if state.report.interview_json:
                    update_data['interview_json'] = json.dumps(state.report.interview_json, ensure_ascii=False)
                if state.report.qa_analysis:
                    update_data['qa_analysis'] = json.dumps(state.report.qa_analysis, ensure_ascii=False)
                if state.report.resume_analysis:
                    update_data['resume_analysis'] = state.report.resume_analysis
                if state.report.interview_evaluation:
                    update_data['interview_evaluation'] = state.report.interview_evaluation
                if state.report.self_evaluation:
                    update_data['self_evaluation'] = state.report.self_evaluation
                if state.report.analysis_end:
                    update_data['analysis_end'] = state.report.analysis_end
                # 存储 MinIO 报告路径
                if getattr(state, 'minio_path', None):
                    update_data['report_file_path'] = state.minio_path

            # 5. 更新状态和错误信息
            if status:
                update_data['status'] = status
            if error_msg:
                update_data['error_msg'] = error_msg

            # 6. 如果状态是 completed 或 failed，设置完成时间
            if status in ('completed', 'failed'):
                update_data['completed_at'] = datetime.now()

            # 7. 执行更新
            if update_data:
                logger.info(f"更新数据字段：{list(update_data.keys())}")
                success = record.update(**update_data)
                if success:
                    logger.info(f"记录更新成功，uuid={record.record_uuid}, status={record.status}")
                else:
                    logger.warning(f"记录更新返回 False，uuid={record.record_uuid}")
                return success
            else:
                logger.info(f"没有需要更新的数据")
                # 即使没有数据，也要更新状态
                if status:
                    return record.update(status=status, completed_at=datetime.now() if status == 'completed' else None)
                return True

        except Exception as e:
            logger.error(f"update_record_from_state 失败：{e}", exc_info=True)
            return False

    @staticmethod
    def save_with_error(state: 'IAState', error_msg: str, node_name: str = None) -> bool:
        """
        保存错误记录（当节点执行失败时调用）

        Args:
            state: IAState 实例
            error_msg: 错误信息
            node_name: 失败的节点名称（可选）

        Returns:
            是否保存成功
        """
        full_error = f"[{node_name}] {error_msg}" if node_name else error_msg
        logger.error(f"保存错误记录：{full_error}")

        # 尝试查找并更新现有记录
        updated = InterviewRecordService.update_record_from_state(
            state=state,
            status='failed',
            error_msg=full_error
        )

        if not updated:
            # 如果没有现有记录，创建一个新的失败记录
            try:
                record = InterviewRecordPo(
                    user_name=state.api_params.user_name or '',
                    user_email=state.api_params.receive_email,
                    company_name=state.api_params.company_name,
                    status='failed',
                    error_msg=full_error,
                    completed_at=datetime.now()
                )
                record_id = record.save()
                if record_id > 0:
                    logger.info(f"错误记录创建成功，id={record_id}")
                    return True
                else:
                    logger.error(f"错误记录创建失败，save 返回 id={record_id}")
                    return False
            except Exception as e:
                logger.error(f"save_with_error 创建记录失败：{e}", exc_info=True)
                return False

        return True

    @staticmethod
    def save_final_record(state: 'IAState', record_uuid: str = None) -> bool:
        """
        保存最终记录（工作流完成时调用）

        Args:
            state: IAState 实例
            record_uuid: 记录 UUID（可选）

        Returns:
            是否保存成功
        """
        try:
            success = InterviewRecordService.update_record_from_state(
                state=state,
                record_uuid=record_uuid,
                status='completed'
            )
            if success:
                logger.info(f"最终记录保存成功")
            else:
                logger.warning(f"最终记录保存失败")
            return success
        except Exception as e:
            logger.error(f"save_final_record 失败：{e}", exc_info=True)
            return False


# 单例实例
_interview_record_service = InterviewRecordService()


def get_interview_record_service() -> InterviewRecordService:
    """获取 InterviewRecordService 单例"""
    return _interview_record_service


if __name__ == '__main__':
    import sys
    sys.path.insert(0, r'C:\Ric\Project\ric-train')

    # 延迟导入 IAState，避免循环依赖
    from Wolin.ai.interview.iaState import IAState

    # 测试代码
    print("=== InterviewRecordService 测试 ===\n")

    # 测试 1：创建初始记录
    state = IAState()
    state.api_params.user_name = '李四'
    state.api_params.receive_email = '1124317604@qq.com'
    state.api_params.company_name = '武当'
    state.ric_id = 'test-001'

    # 模拟完整的 state 数据
    state.asr_info.audio_path = 'test/audio.m4a'
    state.asr_info.audio_text = '这是测试音频文本内容...' * 100
    state.asr_info.qa_pairs = [
        {'question': '请自我介绍', 'answer': '你好，我是...'},
        {'question': '你的优势是什么', 'answer': '我的优势是...'}
    ]

    state.resume_info.name = '李四'
    state.resume_info.age = 25
    state.resume_info.education = '本科'
    state.resume_info.major = '计算机科学与技术'

    state.report.analysis_start = '面试报告开篇语...'
    state.report.interview_json = {'score': 85, 'level': 'A', 'items': [{'name': '技术能力', 'score': 90}]}
    state.report.qa_analysis = {'total_questions': 10, 'good_answers': 7, 'suggestions': ['加强沟通']}
    state.report.resume_analysis = '简历分析内容...'
    state.report.interview_evaluation = '面试官评价：表现良好'
    state.report.self_evaluation = '自我评价：有待提高'
    state.report.analysis_end = '报告结束语...'

    record = InterviewRecordService.create_initial_record(state)
    if record:
        print(f'初始记录创建成功，id={record.id}, uuid={record.record_uuid}')

        # 测试 2：更新记录（模拟工作流完成）
        success = InterviewRecordService.save_final_record(state=state, record_uuid=record.record_uuid)
        print(f'最终记录保存（完整数据）: {"成功" if success else "失败"}')

        if success:
            # 验证数据是否正确保存
            saved_record = InterviewRecordPo.find_one_by(record_uuid=record.record_uuid)
            if saved_record:
                print(f'\n=== 验证保存的数据 ===')
                print(f'  user_name: {saved_record.user_name}')
                print(f'  audio_text 长度：{len(saved_record.audio_text) if saved_record.audio_text else 0}')
                print(f'  qa_pairs: {saved_record.get_qa_pairs}')
                print(f'  resume_info: {saved_record.get_resume_info}')
                print(f'  interview_json: {saved_record.get_interview_json}')
                print(f'  status: {saved_record.status}')
            else:
                print('无法查询到保存的记录')
    else:
        print('初始记录创建失败')

    print('\n=== 测试完成 ===')
