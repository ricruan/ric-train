import tempfile
import os
from typing import Callable, Any

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


def str_list_2_temp_file(strs: list[str],func: Callable[[str], Any]):
    """
    字符串数组转化为临时文件， 用完记得手动删
    :param strs: 待写成文件的字符串数组
    :param func: 对临时文件操作的函数
    :return:
    """
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
            # 写入每行（添加换行符）
            for line in strs:
                tmp_file.write(line + '\n')

            # 刷新确保内容写入磁盘（某些场景需要）
            tmp_file.flush()
            temp_file_path = tmp_file.name
        return func(temp_file_path)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)