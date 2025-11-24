import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


def get_log_level_from_env():
    """
    从环境变量中获取日志级别设置

    Returns:
        int: 日志级别对应的数值
    """
    # 从环境变量获取日志级别，默认为INFO
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()

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


def setup_logging():
    """
    配置日志系统，按天生成日志文件，日志级别从环境变量中获取
    """
    # 创建logs目录（如果不存在）
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 创建日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 从环境变量获取日志级别
    log_level = get_log_level_from_env()

    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # 添加按天轮转的文件处理器
    log_file_path = log_dir / "app.log"
    file_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when='midnight',  # 每天午夜轮转
        interval=1,  # 每1天轮转一次
        backupCount=30,  # 保留30天的日志
        encoding='utf-8',
        atTime=None  # 在午夜时分轮转
    )
    # 设置后缀名格式为 .YYYY-MM-DD
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # 添加专门用于ERROR级别日志的文件处理器
    error_log_file_path = log_dir / "app.error.log"
    error_file_handler = TimedRotatingFileHandler(
        filename=error_log_file_path,
        when='midnight',  # 每天午夜轮转
        interval=1,  # 每1天轮转一次
        backupCount=30,  # 保留30天的日志
        encoding='utf-8',
        atTime=None  # 在午夜时分轮转
    )
    # 设置后缀名格式为 .YYYY-MM-DD
    error_file_handler.suffix = "%Y-%m-%d"
    error_file_handler.setFormatter(log_format)
    # 只处理ERROR及以上级别的日志
    error_file_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_file_handler)

    # 获取日志级别的名称
    level_name = logging.getLevelName(log_level)

    logging.info(f"日志系统初始化完成，日志级别设置为: {level_name}")
    logging.info(f"常规日志文件将保存在: {log_file_path}")
    logging.info(f"错误日志文件将保存在: {error_log_file_path}")
