import logging
from threading import Lock
import time
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

class EarlyStop(Exception):
    """早停,此异常用于提前结束函数，非业务或功能异常"""
    pass

# todo 之前用过一次 好像会有问题
def singleton(cls):
    """
    单例模式装饰器
    :param cls:
    :return:
    """
    instances = {}
    lock = Lock()

    def get_instance(*args, **kwargs):
        # 双重检查，先检查不加锁，再加锁检查
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def timing_log(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    装饰器：在函数执行前后打印开始时间、结束时间和运行耗时。
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        logger.debug(f"[{func.__name__}] 开始执行时间: {start_str}")

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
            elapsed = end_time - start_time
            logger.debug(f"[{func.__name__}] 结束执行时间: {end_str} | 耗时: {elapsed:.4f} 秒")

    return wrapper

def params_handle_4c(before_func):
    """
    参数预处理
    4c 适用于类的方法 内部调用   args[0] 等同于 self
    :param before_func:
    :return:
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                new_params = before_func(args[0], kwargs) or {}
            except EarlyStop :
                return None
            # 先执行原函数
            result = func(*args, **{**kwargs, **new_params})
            # 再执行“之后”的函数
            return result
        return wrapper
    return decorator

def after_exec_4c(after_func):
    """
    在函数执行完成之后，将结果交给另外一个函数执行
    4c 适用于类的方法 内部调用   args[0] 等同于 self
    :param after_func:
    :return:
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 先执行原函数
            result = func(*args, **kwargs)
            # 再执行“之后”的函数
            after_func(args[0],result)
            return result
        return wrapper
    return decorator

def after_exec_4c_no_params(after_func):
    """
    在函数执行完成之后，不传递第一个参数的结果 调用另外一个函数
    4c 适用于类的方法 内部调用   args[0] 等同于 self
    :param after_func:
    :return:
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 先执行原函数
            result = func(*args, **kwargs)
            # 再执行“之后”的函数
            after_func(args[0])
            return result
        return wrapper
    return decorator

def after_exec(after_func):
    """
    在函数执行完成之后，将结果交给另外一个函数执行
    :param after_func:
    :return:
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 先执行原函数
            result = func(*args, **kwargs)
            # 再执行“之后”的函数
            after_func(result)
            return result
        return wrapper
    return decorator