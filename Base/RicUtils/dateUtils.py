from datetime import datetime


def get_current_date():
    """
    获取当前日期并格式化为 yyyy-MM-dd 形式的字符串

    Returns:
        str: 格式为 yyyy-MM-dd 的当前日期字符串
    """
    return datetime.now().strftime("%Y-%m-%d")
