import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from threading import Lock

from Base.Config.setting import settings
from Base.RicUtils.pathUtils import find_project_root


# 模块级单例状态：同一进程共享一把锁和一次成功初始化。
_logging_lock = Lock()
_logging_initialized = False


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }

    # 重置颜色代码
    RESET = '\033[0m'

    def __init__(self, fmt=None, datefmt=None, use_color=True):
        """初始化格式化器

        Args:
            fmt: 日志格式字符串
            datefmt: 日期格式字符串
            use_color: 是否使用颜色
        """
        super().__init__(fmt, datefmt)
        self.use_color = use_color

    def format(self, record):
        """格式化日志记录

        Args:
            record: 日志记录对象

        Returns:
            格式化后的日志字符串
        """
        # 调用父类的format方法获取基本格式
        log_message = super().format(record)

        # 如果启用颜色且输出到控制台，则添加颜色
        if self.use_color and hasattr(record, 'levelname'):
            levelname = record.levelname
            color = self.COLORS.get(levelname, '')
            if color:
                # 为整个日志消息添加颜色
                log_message = color + log_message + self.RESET

        return log_message


def get_log_level_from_env():
    """
    从环境变量中获取日志级别设置

    Returns:
        int: 日志级别对应的数值
    """
    # 从环境变量获取日志级别，默认为INFO
    log_level_str = settings.log_level

    # 日志级别映射
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    # 返回对应的日志级别，如果环境变量值无效则默认使用INFO
    return log_levels.get(log_level_str, logging.INFO)


def setup_logging(project_name: str = "app"):
    """
    线程安全地初始化当前进程的日志系统，仅首次成功调用生效。

    后续调用复用根 logger 和已有处理器，不改变项目名或日志级别。
    多 worker 部署时各进程独立初始化，日志文件继续通过 PID 区分。

    Args:
        project_name: 首次初始化时的项目名称，默认为 "app"
    """
    global _logging_initialized

    with _logging_lock:
        if _logging_initialized:
            return

        root_logger = logging.getLogger()
        previous_level = root_logger.level
        handlers = []
        try:
            _configure_logging(project_name, root_logger, handlers)
        except Exception:
            # 失败时仅清理本次创建的处理器，允许下一次调用重试。
            for handler in handlers:
                root_logger.removeHandler(handler)
                handler.close()
            root_logger.setLevel(previous_level)
            raise
        _logging_initialized = True


def _configure_logging(project_name, root_logger, handlers):
    """在初始化锁内创建处理器；全部准备好后再挂载到根 logger。"""
    # 创建logs目录（如果不存在）
    project_root = find_project_root()
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)

    # 获取当前日期（年月日）
    date_str = datetime.now().strftime('%Y-%m-%d')

    # 创建日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建带颜色的日志格式化器（仅用于控制台输出）
    colored_format = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        use_color=True
    )

    # 从环境变量获取日志级别
    log_level = get_log_level_from_env()

    # 添加控制台处理器（使用带颜色的格式化器）
    console_handler = logging.StreamHandler(sys.stdout)
    handlers.append(console_handler)
    console_handler.setFormatter(colored_format)

    # 添加按天轮转的文件处理器
    # 使用 PID 区分进程，避免多实例同时运行时文件锁冲突 (Windows WinError 32)
    import os
    pid = os.getpid()
    log_file_path = log_dir / f"{project_name}-{date_str}-{pid}.log"
    file_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when='midnight',  # 每天午夜轮转
        interval=1,  # 每1天轮转一次
        backupCount=7,  # 保留7天（多进程会产生多个文件，减少保留天数）
        encoding='utf-8',
        atTime=None  # 在午夜时分轮转
    )
    handlers.append(file_handler)
    # 设置后缀名格式为 .YYYY-MM-DD
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(log_format)

    # 添加专门用于ERROR级别日志的文件处理器
    error_log_file_path = log_dir / f"{project_name}-{date_str}-{pid}.error.log"
    error_file_handler = TimedRotatingFileHandler(
        filename=error_log_file_path,
        when='midnight',  # 每天午夜轮转
        interval=1,  # 每1天轮转一次
        backupCount=7,  # 保留7天
        encoding='utf-8',
        atTime=None  # 在午夜时分轮转
    )
    handlers.append(error_file_handler)
    # 设置后缀名格式为 .YYYY-MM-DD
    error_file_handler.suffix = "%Y-%m-%d"
    error_file_handler.setFormatter(log_format)
    # 只处理ERROR及以上级别的日志
    error_file_handler.setLevel(logging.ERROR)
    root_logger.setLevel(log_level)
    for handler in handlers:
        root_logger.addHandler(handler)

    # 获取日志级别的名称
    level_name = logging.getLevelName(log_level)

    logging.info(f"日志系统初始化完成，日志级别: {level_name}, PID: {pid}")
    logging.info(f"常规日志: {log_file_path}")
    logging.info(f"错误日志: {error_log_file_path}")

    # 屏蔽第三方库的 DEBUG 日志
    logging.getLogger("python_multipart").setLevel(logging.WARNING)
