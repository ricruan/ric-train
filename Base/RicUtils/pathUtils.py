from pathlib import Path

def find_project_root(marker_files=None):
    """
    从当前文件向上查找项目根目录，依据是否存在 marker_files 中的任一文件。

    Args:
        marker_files: 用于识别根目录的文件名列表，如 ['.env', 'pyproject.toml', 'requirements.txt']

    Returns:
        Path: 项目根目录的 Path 对象
    """
    if marker_files is None:
        marker_files = ['.env', 'pyproject.toml', 'requirements.txt', '.git']

    current_path = Path(__file__).resolve().parent
    while current_path != current_path.parent:  # 防止无限循环到根目录
        if any((current_path / marker).exists() for marker in marker_files):
            return current_path
        current_path = current_path.parent
    # 如果没找到，回退到当前文件所在目录的父级（或抛异常）
    return Path(__file__).resolve().parent.parent  # 保守回退