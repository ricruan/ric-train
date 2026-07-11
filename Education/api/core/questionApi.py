import concurrent.futures
import logging
import random
import threading
import uuid
from datetime import datetime
from dbm.dumb import error
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Response, UploadFile, File, Query, Form, Body
from pydantic import BaseModel

from Base.RicUtils.dataUtils import remove_none
from Base.RicUtils.excelUtils import dict_list_to_excel, excel_to_dict_list
from Base.RicUtils.httpUtils import HttpResponse
from Education.models.pojo.questionBo import AiJudgeQuestionBo, QuestionRandomBo, QuestionImportBo
from Education.models.pojo.questionPo import QuestionPo
from Education.models.pojo.questionVo import QuestionRandomParamVo
from Education.services.questionService import get_question_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/education/question")


# =========================
# Request Models (JSON)
# =========================

class CreateQuestionRequest(BaseModel):
    question_text: str
    answer: str
    grade: int
    subject: str
    question_type: str
    question_html: Optional[str] = None
    question_markdown: Optional[str] = None
    analysis: Optional[str] = None
    hint: Optional[str] = None
    knowledge_points: Optional[str] = None
    ai_judge_prompt: Optional[str] = None
    difficulty_level: Optional[int] = 3
    difficulty_label: Optional[str] = None
    created_by: Optional[int] = 505


class UpdateQuestionRequest(BaseModel):
    question_text: str
    answer: str
    grade: int
    subject: str
    question_type: str
    question_html: Optional[str] = None
    question_markdown: Optional[str] = None
    analysis: Optional[str] = None
    hint: Optional[str] = None
    knowledge_points: Optional[str] = None
    ai_judge_prompt: Optional[str] = None
    difficulty_level: Optional[int] = 3
    difficulty_label: Optional[str] = None
    updated_by: Optional[int] = 505


@router.get("/subjects")
def get_subjects():
    """
    获取科目列表

    Returns:
        科目列表
    """
    try:
        subjects = get_question_service().get_subjects()
        return HttpResponse.ok(subjects)
    except Exception as e:
        logger.error(f"获取科目列表失败：{str(e)}")
        return HttpResponse.error(f"获取科目列表失败：{str(e)}")


@router.get("/random_one")
def get_random_one_question(
    user_id: str = Query(None, description="用户ID"),
    subject: Optional[str] = Query(None, description="科目"),
    question_type: Optional[str] = Query(None, description="题型"),
    difficulty_level: Optional[int] = Query(None, description="难度等级 1-5"),
    grade: Optional[int] = Query(None, description="年级 1-12"),
    num: Optional[int] = Query(1, description="题目数量，默认1道")
):
    """
    随机返回题目

    Args:
        user_id: 用户ID
        subject: 科目筛选（可选）
        question_type: 题型筛选（可选）
        difficulty_level: 难度等级筛选 1-5（可选）
        grade: 年级筛选 1-12（可选）
        num: 题目数量，默认1道

    Returns:
        num=1 时返回单个题目对象，num>1 时返回题目列表
    """
    # todo: 不返回用户已经做过的题目
    num = num or 1

    # 一次性查询 num 道题目
    questions = QuestionPo.get_random_question(
        user_id=user_id,
        subject=subject,
        question_type=question_type,
        difficulty_level=difficulty_level,
        grade=grade,
        num=num
    )

    if num == 1:
        # 返回单道题目
        return HttpResponse.ok(questions.mini_dict if questions else None)
    else:
        # 返回多道题目
        return HttpResponse.ok([q.mini_dict for q in questions])


@router.post("/random_generate")
async def generate_random_question(params: QuestionRandomParamVo):
    """
    随机AI生成题目接口
    :param params:  如果不指定对应参数的值，对应参数将随机取值。 如 不指定 科目，将随机取一个科目
    :return:
    """

    # 多线程并发执行，同时启动多个线程并发生成，加快生成速度
    def generate_single_question(params):
        """生成单个题目"""
        try:
            get_question_service().random_generate_question(params)
        except Exception as e:
            logger.error(f"生成题目失败：{str(e)}")

    # 使用线程池并发执行
    max_workers = min(params.num, 20)  # 限制最大并发数

    def generate_questions():
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有生成任务
            futures = [executor.submit(generate_single_question, params) for _ in range(params.num)]
            # 等待所有任务完成
            concurrent.futures.wait(futures)

    # 在额外线程中执行
    threading.Thread(target=generate_questions).start()
    return HttpResponse.ok(f"正在生成 {params.num} 道题目...")


@router.post("/ai_judge")
async def ai_judge_question(params: AiJudgeQuestionBo):
    """
    AI判题接口
    """
    res = get_question_service().ai_judge_question(params)
    return HttpResponse.ok(res)

@router.post("/judge")
async def judge_question(params: AiJudgeQuestionBo):
    """
    人工判题接口
    """
    res = get_question_service().judge_question(params)
    return HttpResponse.ok(res)


@router.post("/excel_export")
async def excel_export_question(params: QuestionRandomBo):
    """
    导出题目到Excel接口

    支持根据参数筛选导出：
    - subject: 科目筛选（可选）
    - question_type: 题型筛选（可选）
    - difficulty_level: 难度筛选（可选）
    - grade_type: 年级筛选（可选）

    返回 Excel 文件下载
    """
    # 查询题目数据
    questions = QuestionPo.find_by(**remove_none(params.model_dump()))

    # 转换为字典列表（使用 model_dump 返回所有字段，包括空值）
    data_list = [q.model_dump() for q in questions]

    # 如果没有数据
    if not data_list:
        return HttpResponse.error("没有可导出的题目数据")

    # 字段名映射（英文 -> 中文），从模型中获取
    field_name_map = QuestionPo.get_field_mapping()
    # 额外添加一些自定义映射（覆盖或补充模型定义）
    field_name_map.update({
        'id': 'ID',
        'question_uuid': '题目UUID',
    })

    # 排除字段（敏感或不必要的字段）
    exclude_fields = [
        'ai_judge_prompt',
        'ai_prompt',
        'ai_params',
        'change_log',
        'previous_version_id'
    ]

    # 生成 Excel 文件
    filename = f"题目导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    # 对文件名进行 URL 编码，支持中文
    encoded_filename = quote(filename)
    excel_bytes = dict_list_to_excel(
        data_list,
        sheet_name="题目列表",
        field_name_map=field_name_map,
        exclude_fields=exclude_fields,
        include_all_fields=True
    )

    # 返回 Excel 文件
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )


@router.post("/excel_import")
async def excel_import_question(file: UploadFile = File(...)):
    """
    Excel 导入题目接口

    支持上传 Excel 文件批量导入题目。
    Excel 格式应与导出格式保持一致，但可以省略 ID 和 UUID 字段（自动生成）。

    Args:
        file: 上传的 Excel 文件

    Returns:
        导入结果信息

    Example:
        使用 curl 上传：
        curl -X POST "http://localhost:8000/education/question/excel_import" \
             -F "file=@questions.xlsx"

        使用 Postman：
        1. 选择 POST 方法
        2. URL: http://localhost:8000/education/question/excel_import
        3. Body -> form-data
        4. Key: file, Type: File, Value: 选择 Excel 文件
    """
    import io

    # 检查文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        return HttpResponse.error("文件格式错误，请上传 Excel 文件（.xlsx 或 .xls）")

    try:
        # 读取文件内容
        file_content = await file.read()
        file_obj = io.BytesIO(file_content)

        # 字段名映射（中文 -> 英文），从模型中获取并反转
        field_mapping_en_to_cn = QuestionPo.get_field_mapping()
        field_name_map = {cn: en for en, cn in field_mapping_en_to_cn.items()}
        # 额外添加一些自定义映射
        field_name_map.update({
            'ID': 'id',
            '题目UUID': 'question_uuid',
        })

        # 解析 Excel
        data_list = excel_to_dict_list(
            file_obj=file_obj,
            field_name_map=field_name_map
        )

        if not data_list:
            return HttpResponse.error("Excel 文件为空或格式不正确")

        # 转换为 QuestionPo 对象列表
        questions = []
        created_by = 505  # 默认创建人 ID（可根据实际需求修改）

        for data in data_list:
            # 过滤掉空值字段
            data = {key: value for key, value in data.items() if value}

            # 自动生成 question_uuid
            data['question_uuid'] = str(uuid.uuid4())

            # 设置默认创建人
            if 'created_by' not in data or not data['created_by']:
                data['created_by'] = created_by

            # 处理类型转换问题

            # 1. 处理布尔值转字符串（如 answer: False -> "False"）
            if 'answer' in data and isinstance(data['answer'], bool):
                data['answer'] = str(data['answer'])

            # 2. 处理 datetime 字段（created_at, updated_at 为 None）
            if 'created_at' in data and data['created_at'] is None:
                data['created_at'] = datetime.now()
            if 'updated_at' in data and data['updated_at'] is None:
                data['updated_at'] = datetime.now()

            # 3. 处理整数类型（created_by, updated_by）
            if 'created_by' in data and isinstance(data['created_by'], str):
                try:
                    data['created_by'] = int(data['created_by'])
                except (ValueError, TypeError):
                    data['created_by'] = created_by
            if 'updated_by' in data and isinstance(data['updated_by'], str):
                try:
                    data['updated_by'] = int(data['updated_by'])
                except (ValueError, TypeError):
                    data['updated_by'] = None  # updated_by 是 Optional[int]

            # 4. 验证必需字段（过滤后可能被移除）
            required_fields = ['question_text', 'grade', 'subject', 'question_type', 'question_uuid', 'created_by']
            missing_fields = [field for field in required_fields if field not in data or not data[field]]
            if missing_fields:
                logger.warning(f"跳过缺少必需字段的数据行：缺少 {missing_fields}, 数据：{data}")
                continue

            # 5. 保留所有字段，不强制转换为None（让Pydantic根据Optional定义处理）

            # 创建 QuestionPo 对象
            try:
                question = QuestionPo(**data)
                questions.append(question)
            except Exception as e:
                logger.warning(f"跳过无效数据行：{data}, 错误：{str(e)}")
                continue

        if not questions:
            return HttpResponse.error("没有有效的题目数据可导入")

        # 批量插入
        inserted_ids = QuestionPo.bulk_insert(questions, batch_size=100)

        return HttpResponse.ok({
            "message": f"成功导入 {len(inserted_ids)} 道题目",
            "total_rows": len(data_list),
            "valid_rows": len(questions),
            "inserted_rows": len(inserted_ids),
            "skipped_rows": len(data_list) - len(questions)
        })

    except ValueError as e:
        return HttpResponse.error(f"读取 Excel 失败：{str(e)}")
    except Exception as e:
        logger.error(f"导入题目失败：{str(e)}")
        return HttpResponse.error(f"导入失败：{str(e)}")


@router.get("/search")
def search_questions(
    keyword: Optional[str] = Query(None, description="关键词"),
    subject: Optional[str] = Query(None, description="科目"),
    question_type: Optional[str] = Query(None, description="题型"),
    grade: Optional[int] = Query(None, description="年级"),
    difficulty_level: Optional[int] = Query(None, description="难度等级"),
    page: Optional[int] = Query(1, description="页码"),
    page_size: Optional[int] = Query(10, description="每页数量")
):
    """
    搜索题目

    Args:
        keyword: 关键词（搜索题干）
        subject: 科目
        question_type: 题型
        grade: 年级
        difficulty_level: 难度等级
        page: 页码
        page_size: 每页数量

    Returns:
        分页结果
    """
    try:
        result = QuestionPo.search(
            keyword=keyword,
            subject=subject,
            question_type=question_type,
            grade=grade,
            difficulty_level=difficulty_level,
            page=page or 1,
            page_size=page_size or 10
        )
        return HttpResponse.ok(result)
    except Exception as e:
        logger.error(f"搜索题目失败：{str(e)}")
        return HttpResponse.error(f"搜索题目失败：{str(e)}")


@router.get("/{question_id}")
def get_question_detail(question_id: int):
    """
    获取题目详情

    Args:
        question_id: 题目 ID

    Returns:
        题目详情
    """
    try:
        question = QuestionPo.get_by_id(question_id)
        if not question:
            return HttpResponse.error("题目不存在")
        return HttpResponse.ok(question.model_dump())
    except Exception as e:
        logger.error(f"获取题目详情失败：{str(e)}")
        return HttpResponse.error(f"获取题目详情失败：{str(e)}")


@router.post("")
def create_question(req: CreateQuestionRequest):
    """
    创建题目

    Args:
        req: 题目数据（JSON）

    Returns:
        创建的题目信息
    """
    try:
        question = QuestionPo(
            question_uuid=str(uuid.uuid4()),
            question_text=req.question_text,
            question_html=req.question_html,
            question_markdown=req.question_markdown,
            answer=req.answer,
            analysis=req.analysis,
            hint=req.hint,
            knowledge_points=req.knowledge_points,
            ai_judge_prompt=req.ai_judge_prompt,
            grade=req.grade,
            subject=req.subject,
            question_type=req.question_type,
            difficulty_level=req.difficulty_level,
            difficulty_label=req.difficulty_label,
            created_by=req.created_by or 505,
            status=0
        )
        question.save()

        return HttpResponse.ok({
            'id': question.id,
            'question_uuid': question.question_uuid,
            'message': '题目创建成功'
        })
    except Exception as e:
        logger.error(f"创建题目失败：{str(e)}")
        return HttpResponse.error(f"创建题目失败：{str(e)}")


@router.put("/{question_id}")
def update_question(question_id: int, req: UpdateQuestionRequest):
    """
    更新题目

    Args:
        question_id: 题目 ID
        req: 题目数据（JSON）

    Returns:
        更新后的题目信息
    """
    try:
        question = QuestionPo.get_by_id(question_id)
        if not question:
            return HttpResponse.error("题目不存在")

        # 更新字段
        question.question_text = req.question_text
        question.question_html = req.question_html
        question.question_markdown = req.question_markdown
        question.answer = req.answer
        question.analysis = req.analysis
        question.hint = req.hint
        question.knowledge_points = req.knowledge_points
        question.ai_judge_prompt = req.ai_judge_prompt
        question.grade = req.grade
        question.subject = req.subject
        question.question_type = req.question_type
        question.difficulty_level = req.difficulty_level
        question.difficulty_label = req.difficulty_label
        question.updated_by = req.updated_by or 505

        question.save()

        return HttpResponse.ok({
            'id': question.id,
            'message': '题目更新成功'
        })
    except Exception as e:
        logger.error(f"更新题目失败：{str(e)}")
        return HttpResponse.error(f"更新题目失败：{str(e)}")


@router.delete("/{question_id}")
def delete_question(question_id: int):
    """
    删除题目（软删除）

    Args:
        question_id: 题目 ID

    Returns:
        操作结果
    """
    try:
        question = QuestionPo.get_by_id(question_id)
        if not question:
            return HttpResponse.error("题目不存在")

        # 软删除：设置 status=1
        question.status = 1
        question.save()

        return HttpResponse.ok({'message': '题目删除成功'})
    except Exception as e:
        logger.error(f"删除题目失败：{str(e)}")
        return HttpResponse.error(f"删除题目失败：{str(e)}")


@router.post("/import/text")
async def import_questions_from_text(params: QuestionImportBo):
    """
    AI 解析文本导入题目接口

    用户输入包含题目的文本，AI 自动解析并批量插入到题目表。

    Args:
        params: 导入参数
            - text: 包含题目的文本
            - subject: 科目（必填）
            - grade_range: 年级范围（如 "1-6" 小学，"7-9" 初中，"10-12" 高中）
            - difficulty: 默认难度（1-5）
            - question_type: 指定题型（可选）
            - created_by: 创建人 ID

    Returns:
        导入结果：
            - success: 成功导入数量
            - failed: 失败数量
            - questions: 导入成功的题目列表
            - errors: 错误信息

    Example:
        {
            "text": "1. Python 是什么语言？\n   A. 编译型 B. 解释型...\n   答案：B",
            "subject": "python",
            "grade_range": "7-9",
            "difficulty": 3
        }
    """
    try:
        result = get_question_service().import_questions_from_text(
            text=params.text,
            subject=params.subject,
            grade_range=params.grade_range,
            difficulty=params.difficulty,
            question_type=params.question_type,
            created_by=params.created_by
        )
        return HttpResponse.ok(result)
    except Exception as e:
        logger.error(f"导入题目失败：{str(e)}")
        return HttpResponse.error(f"导入失败：{str(e)}")


@router.post("/import/file")
async def import_questions_from_file(
    file: UploadFile = File(...),
    subject: str = Form(..., description="科目"),
    grade_range: str = Form("7-9", description="年级范围"),
    difficulty: int = Form(3, description="默认难度"),
    question_type: str = Form(None, description="指定题型")
):
    """
    上传文件导入题目接口

    支持 .txt, .md, .docx 文件格式。

    Args:
        file: 上传的文件
        subject: 科目（必填）
        grade_range: 年级范围
        difficulty: 默认难度
        question_type: 指定题型

    Returns:
        导入结果（同 text 接口）

    Example:
        curl -X POST "http://localhost:8000/education/question/import/file" \\
             -F "file=@questions.txt" \\
             -F "subject=python" \\
             -F "grade_range=7-9"
    """
    # 检查文件类型
    allowed_extensions = ['.txt', '.md', '.docx']
    file_ext = None
    if file.filename:
        for ext in allowed_extensions:
            if file.filename.endswith(ext):
                file_ext = ext
                break

    if not file_ext:
        return HttpResponse.error(f"不支持的文件格式，仅支持：{', '.join(allowed_extensions)}")

    try:
        # 读取文件内容
        file_content = await file.read()
        text = file_content.decode('utf-8')

        # 调用文本导入接口
        result = get_question_service().import_questions_from_text(
            text=text,
            subject=subject,
            grade_range=grade_range,
            difficulty=difficulty,
            question_type=question_type
        )

        return HttpResponse.ok(result)

    except UnicodeDecodeError as e:
        logger.error(f"文件编码错误：{str(e)}")
        return HttpResponse.error(f"文件编码错误，请使用 UTF-8 编码：{str(e)}")
    except Exception as e:
        logger.error(f"导入题目失败：{str(e)}")
        return HttpResponse.error(f"导入失败：{str(e)}")
