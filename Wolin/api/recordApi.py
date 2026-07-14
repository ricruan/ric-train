import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Form, Query

from Base.Client.minioClient import default_minio_client
from Base.RicUtils.httpUtils import HttpResponse
from Wolin.models.po.interviewRecordPo import InterviewRecordPo

router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize_record(record: InterviewRecordPo) -> dict:
    """将 PO 对象序列化为可 JSON 序列化的字典"""
    data = record.model_dump()
    for field_name in ('qa_pairs', 'resume_info', 'interview_json', 'qa_analysis'):
        value = data.get(field_name)
        if isinstance(value, str) and value and value.strip():
            try:
                import json
                data[field_name] = json.loads(value)
            except Exception:
                data[field_name] = None
    for k, v in list(data.items()):
        if isinstance(v, datetime):
            data[k] = v.isoformat()
    return data


# ── 单条 CRUD ──────────────────────────────────────────────

@router.post("/record")
async def create_record(
        user_name: str = Form(...),
        user_email: Optional[str] = Form(None),
        company_name: Optional[str] = Form(None),
        status: str = Form('processing'),
):
    try:
        record = InterviewRecordPo(
            user_name=user_name,
            user_email=user_email,
            company_name=company_name,
            status=status,
        )
        record_id = record.save()
        if record_id > 0:
            return HttpResponse.ok(data=_serialize_record(record), msg="创建成功")
        return HttpResponse.error(msg="创建失败")
    except Exception as e:
        logger.error(f"create_record 失败：{e}", exc_info=True)
        return HttpResponse.error(msg=f"创建失败：{str(e)}")


@router.get("/record/{record_id}")
async def get_record(record_id: int):
    try:
        record = InterviewRecordPo.get_by_id(record_id)
        if not record:
            return HttpResponse.error(msg="记录不存在")
        return HttpResponse.ok(data=_serialize_record(record))
    except Exception as e:
        logger.error(f"get_record 失败：{e}", exc_info=True)
        return HttpResponse.error(msg=f"查询失败：{str(e)}")


@router.put("/record/{record_id}")
async def update_record(
        record_id: int,
        user_name: Optional[str] = Form(None),
        user_email: Optional[str] = Form(None),
        company_name: Optional[str] = Form(None),
        status: Optional[str] = Form(None),
        audio_file_path: Optional[str] = Form(None),
        audio_duration: Optional[int] = Form(None),
        resume_file_path: Optional[str] = Form(None),
        report_file_path: Optional[str] = Form(None),
        analysis_start: Optional[str] = Form(None),
        resume_analysis: Optional[str] = Form(None),
        interview_evaluation: Optional[str] = Form(None),
        self_evaluation: Optional[str] = Form(None),
        analysis_end: Optional[str] = Form(None),
        error_msg: Optional[str] = Form(None),
        audio_text: Optional[str] = Form(None),
        qa_pairs: Optional[str] = Form(None),
        resume_info: Optional[str] = Form(None),
        interview_json: Optional[str] = Form(None),
        qa_analysis: Optional[str] = Form(None),
):
    try:
        record = InterviewRecordPo.get_by_id(record_id)
        if not record:
            return HttpResponse.error(msg="记录不存在")

        fields = {
            'user_name': user_name,
            'user_email': user_email,
            'company_name': company_name,
            'status': status,
            'audio_file_path': audio_file_path,
            'audio_duration': audio_duration,
            'resume_file_path': resume_file_path,
            'report_file_path': report_file_path,
            'analysis_start': analysis_start,
            'resume_analysis': resume_analysis,
            'interview_evaluation': interview_evaluation,
            'self_evaluation': self_evaluation,
            'analysis_end': analysis_end,
            'error_msg': error_msg,
            'audio_text': audio_text,
        }
        update_data = {k: v for k, v in fields.items() if v is not None}

        # JSON 字段单独处理
        for json_field in ('qa_pairs', 'resume_info', 'interview_json', 'qa_analysis'):
            raw = locals()[json_field]
            if raw is not None:
                record.set_json_field(json_field, raw)
                update_data[json_field] = getattr(record, json_field)

        if not update_data:
            return HttpResponse.ok(data=_serialize_record(record), msg="无变更")

        success = record.update(**update_data)
        if success:
            return HttpResponse.ok(data=_serialize_record(record), msg="更新成功")
        return HttpResponse.error(msg="更新失败")
    except Exception as e:
        logger.error(f"update_record 失败：{e}", exc_info=True)
        return HttpResponse.error(msg=f"更新失败：{str(e)}")


@router.delete("/record/{record_id}")
async def delete_record(record_id: int):
    try:
        record = InterviewRecordPo.get_by_id(record_id)
        if not record:
            return HttpResponse.error(msg="记录不存在")
        success = record.delete()
        if success:
            return HttpResponse.ok(msg="删除成功")
        return HttpResponse.error(msg="删除失败")
    except Exception as e:
        logger.error(f"delete_record 失败：{e}", exc_info=True)
        return HttpResponse.error(msg=f"删除失败：{str(e)}")


@router.get("/record/{record_id}/download-url")
async def get_download_urls(record_id: int):
    try:
        record = InterviewRecordPo.get_by_id(record_id)
        if not record:
            return HttpResponse.error(msg="记录不存在")

        import os
        files = {}

        # 音频：优先使用 DB 中存储的实际路径，回退到模板路径
        if record.audio_file_path:
            if default_minio_client.stat_object('audios', record.audio_file_path):
                url = default_minio_client.get_presigned_url('audios', record.audio_file_path, expiry_hours=2)
                if url:
                    files['audio'] = {'url': url, 'label': os.path.basename(record.audio_file_path)}
        elif record.user_name and record.company_name:
            fallback = f"{record.user_name}/{record.user_name}_{record.company_name}.m4a"
            if default_minio_client.stat_object('audios', fallback):
                url = default_minio_client.get_presigned_url('audios', fallback, expiry_hours=2)
                if url:
                    files['audio'] = {'url': url, 'label': f'{record.user_name}_{record.company_name}.m4a'}

        # 音频文本：优先使用 DB 路径，回退到模板路径
        if record.audio_text_path:
            if default_minio_client.stat_object('audio-text', record.audio_text_path):
                url = default_minio_client.get_presigned_url('audio-text', record.audio_text_path, expiry_hours=2)
                if url:
                    files['text'] = {'url': url, 'label': os.path.basename(record.audio_text_path)}
        elif record.user_name and record.company_name:
            fallback = f"{record.user_name}/{record.user_name}_{record.company_name}.txt"
            if default_minio_client.stat_object('audio-text', fallback):
                url = default_minio_client.get_presigned_url('audio-text', fallback, expiry_hours=2)
                if url:
                    files['text'] = {'url': url, 'label': f'{record.user_name}_{record.company_name}.txt'}

        # 音频原始文本：优先使用 DB 路径，回退到模板路径
        if record.audio_text_origin_path:
            if default_minio_client.stat_object('audio-text-origin', record.audio_text_origin_path):
                url = default_minio_client.get_presigned_url('audio-text-origin', record.audio_text_origin_path, expiry_hours=2)
                if url:
                    files['text_origin'] = {'url': url, 'label': os.path.basename(record.audio_text_origin_path)}
        elif record.user_name and record.company_name:
            fallback = f"{record.user_name}/{record.user_name}_{record.company_name}_origin.txt"
            if default_minio_client.stat_object('audio-text-origin', fallback):
                url = default_minio_client.get_presigned_url('audio-text-origin', fallback, expiry_hours=2)
                if url:
                    files['text_origin'] = {'url': url, 'label': f'{record.user_name}_{record.company_name}_origin.txt'}

        # 面试报告：优先使用 DB 路径，回退到模板路径
        if record.report_file_path:
            if default_minio_client.stat_object('interview-report', record.report_file_path):
                url = default_minio_client.get_presigned_url('interview-report', record.report_file_path, expiry_hours=2)
                if url:
                    files['report'] = {'url': url, 'label': os.path.basename(record.report_file_path)}
        elif record.user_name and record.company_name:
            fallback = f"{record.user_name}/{record.user_name}_{record.company_name}.docx"
            if default_minio_client.stat_object('interview-report', fallback):
                url = default_minio_client.get_presigned_url('interview-report', fallback, expiry_hours=2)
                if url:
                    files['report'] = {'url': url, 'label': f'{record.user_name}_{record.company_name}.docx'}

        # 简历：直接使用 DB 中存储的路径
        if record.resume_file_path:
            if default_minio_client.stat_object('resumes', record.resume_file_path):
                url = default_minio_client.get_presigned_url('resumes', record.resume_file_path, expiry_hours=2)
                if url:
                    files['resume'] = {'url': url, 'label': os.path.basename(record.resume_file_path)}

        return HttpResponse.ok(data=files)
    except Exception as e:
        logger.error(f"get_download_urls 失败：{e}", exc_info=True)
        return HttpResponse.error(msg=f"获取下载链接失败：{str(e)}")


# ── 分页+条件查询 ──────────────────────────────────────────

@router.get("/records")
async def list_records(
        user_name: Optional[str] = Query(None, description="用户姓名（模糊）"),
        company_name: Optional[str] = Query(None, description="公司名称（模糊）"),
        user_email: Optional[str] = Query(None, description="邮箱（模糊）"),
        status: Optional[str] = Query(None, description="状态（精确）"),
        created_at_start: Optional[str] = Query(None, description="创建时间起始 YYYY-MM-DD"),
        created_at_end: Optional[str] = Query(None, description="创建时间结束 YYYY-MM-DD"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        order_by: str = Query('created_at', description="排序字段"),
        order: str = Query('DESC', description="排序方向 ASC/DESC"),
):
    try:
        InterviewRecordPo._ensure_table_exists()
        db = InterviewRecordPo.get_db_connection()
        if db is None:
            return HttpResponse.error(msg="数据库连接未设置")

        table_name = InterviewRecordPo.get_table_name_with_db()

        where_clauses = []
        params = []

        if user_name:
            where_clauses.append("`user_name` LIKE %s")
            params.append(f"%{user_name}%")
        if company_name:
            where_clauses.append("`company_name` LIKE %s")
            params.append(f"%{company_name}%")
        if user_email:
            where_clauses.append("`user_email` LIKE %s")
            params.append(f"%{user_email}%")
        if status:
            where_clauses.append("`status` = %s")
            params.append(status)
        if created_at_start:
            where_clauses.append("`created_at` >= %s")
            params.append(created_at_start)
        if created_at_end:
            # 结束日期包含当天全天
            where_clauses.append("`created_at` <= %s")
            params.append(f"{created_at_end} 23:59:59")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # 查总数
        count_sql = f"SELECT COUNT(*) as count FROM {table_name} WHERE {where_sql}"
        count_result = db.execute(count_sql, tuple(params))
        total = count_result[0]['count'] if count_result else 0

        # 查数据
        offset = (page - 1) * page_size
        safe_order_by = order_by if order_by else 'created_at'
        safe_order = order.upper() if order.upper() in ('ASC', 'DESC') else 'DESC'
        data_sql = (
            f"SELECT * FROM {table_name} WHERE {where_sql} "
            f"ORDER BY `{safe_order_by}` {safe_order} "
            f"LIMIT {offset}, {page_size}"
        )
        results = db.execute(data_sql, tuple(params))
        items = [_serialize_record(InterviewRecordPo(**row)) for row in results]

        return HttpResponse.ok(data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })
    except Exception as e:
        logger.error(f"list_records 失败：{e}", exc_info=True)
        return HttpResponse.error(msg=f"查询失败：{str(e)}")
