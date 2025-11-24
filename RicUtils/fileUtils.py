import tempfile
import os
from fastapi import UploadFile


async def save_upload_file_to_temp(
        upload_file: UploadFile,
        use_original_filename: bool = False
) -> str:
    """
    将上传的 UploadFile 保存到系统临时目录中，并返回临时文件的路径。

    Args:
        upload_file (UploadFile): FastAPI 接收到的上传文件对象
        use_original_filename (bool): 是否使用原始文件名作为临时文件名。默认为 False

    Returns:
        str: 临时文件的绝对路径
    """
    temp_file_path = ''
    if use_original_filename:
        # 直接使用原始文件名
        filename = upload_file.filename

        # 获取系统临时目录
        temp_dir = tempfile.gettempdir()

        # 拼接完整的临时文件路径
        temp_file_path = os.path.join(temp_dir, filename)

        # 写入文件内容
        content = await upload_file.read()
        with open(temp_file_path, "wb") as f:
            f.write(content)
    else:
        # 原逻辑：使用临时文件（自动生成唯一文件名，但保留后缀）
        suffix = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await upload_file.read()
            tmp_file.write(content)
            temp_file_path = tmp_file.name

    return temp_file_path