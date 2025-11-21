import json
import pickle
import hashlib
from typing import Any, Optional, Callable
from functools import wraps

def get_default_client():
    """
    获取默认的 Redis 客户端实例
    :return:
    """
    try:
        from Client.redisClient import RedisClient
        return RedisClient()
    except ImportError:
        raise ImportError("无法导入 RedisClient，请提供 redis_client 参数")

def redis_cache(key_template: str,
                expire: Optional[int] = None,
                redis_client=None,
                serializer: str = 'json',
                key_generator: Optional[Callable] = None):
    """
    Redis 缓存装饰器

    Args:
        key_template: Redis 键模板，支持参数占位符，如 "user:{user_id}"
        expire: 过期时间（秒），None 表示永不过期
        redis_client: Redis 客户端实例，如果为 None 则使用默认客户端
        serializer: 序列化方式，'json' 或 'pickle'
        key_generator: 自定义键生成函数，接收函数名、args、kwargs，返回键名

    Usage:
        @redis_cache("user_info:{user_id}", expire=3600)
        def get_user_info(user_id):
            # 复杂的数据库查询
            return database.get_user(user_id)

        @redis_cache("complex_query", expire=1800)
        def complex_calculation(param1, param2):
            # 复杂计算
            return expensive_operation(param1, param2)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取 Redis 客户端
            client = redis_client
            if client is None:
                client = get_default_client()

            # 生成缓存键
            if key_generator:
                cache_key = key_generator(func.__name__, args, kwargs)
            else:
                cache_key = _generate_cache_key(key_template, func.__name__, args, kwargs)

            try:
                # 尝试从 Redis 获取缓存
                cached_value = client.get(cache_key)
                if cached_value is not None:
                    # 反序列化并返回缓存值
                    return _deserialize(cached_value, serializer)
            except Exception as e:
                # 缓存读取失败，记录日志但继续执行原函数
                print(f"Redis 缓存读取失败 {cache_key}: {e}")

            # 缓存未命中，执行原函数
            result = func(*args, **kwargs)

            try:
                # 序列化结果并存入 Redis
                serialized_result = _serialize(result, serializer)
                client.set(cache_key, serialized_result, ex=expire)
            except Exception as e:
                # 缓存写入失败，记录日志但不影响原函数返回
                print(f"Redis 缓存写入失败 {cache_key}: {e}")

            return result

        return wrapper
    return decorator


def _generate_cache_key(key_template: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """
    生成缓存键

    Args:
        key_template: 键模板
        func_name: 函数名
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        生成的缓存键
    """
    # 如果模板包含占位符，尝试格式化
    if '{' in key_template and '}' in key_template:
        try:
            # 将 args 和 kwargs 合并为一个字典
            all_params = {}

            # 获取函数的参数名（简单处理，只考虑位置参数）
            import inspect
            sig = inspect.signature(func_name if callable(func_name) else (lambda: None))
            param_names = list(sig.parameters.keys())

            # 将位置参数映射到参数名
            for i, arg in enumerate(args):
                if i < len(param_names):
                    all_params[param_names[i]] = arg

            # 添加关键字参数
            all_params.update(kwargs)

            # 尝试格式化模板
            try:
                formatted_key = key_template.format(**all_params)
                return formatted_key
            except KeyError:
                # 格式化失败，使用备用方案
                pass
        except Exception:
            # 获取参数信息失败，使用备用方案
            pass

    # 备用方案：基于函数名和参数哈希生成键
    params_str = str(args) + str(sorted(kwargs.items()))
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    return f"{key_template}:{func_name}:{params_hash}"


def _serialize(obj: Any, serializer: str) -> str:
    """
    序列化对象

    Args:
        obj: 要序列化的对象
        serializer: 序列化方式

    Returns:
        序列化后的字符串
    """
    if serializer == 'json':
        try:
            return json.dumps(obj, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            # JSON 序列化失败，尝试使用 pickle
            pass

    # 默认使用 pickle
    if serializer == 'pickle' or True:
        return pickle.dumps(obj).hex()

    raise ValueError(f"不支持的序列化方式: {serializer}")


def _deserialize(data: str, serializer: str) -> Any:
    """
    反序列化对象

    Args:
        data: 要反序列化的数据
        serializer: 序列化方式

    Returns:
        反序列化后的对象
    """
    if serializer == 'json':
        try:
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            # JSON 反序列化失败，尝试使用 pickle
            pass

    # 默认使用 pickle
    if serializer == 'pickle' or True:
        try:
            return pickle.loads(bytes.fromhex(data))
        except (ValueError, pickle.UnpicklingError):
            pass

    raise ValueError(f"反序列化失败，数据: {data[:50]}...")


# 便捷的缓存装饰器
def cache_result(key: str, expire: Optional[int] = None):
    """
    简化的缓存装饰器，适用于无参数函数

    Args:
        key: Redis 键名
        expire: 过期时间（秒）

    Usage:
        @cache_result("expensive_config", expire=300)
        def load_config():
            return load_from_database()
    """
    return redis_cache(key_template=key, expire=expire)


def cache_with_params(key_template: str, expire: Optional[int] = None):
    """
    带参数的缓存装饰器

    Args:
        key_template: 键模板，支持参数占位符
        expire: 过期时间（秒）

    Usage:
        @cache_with_params("user_profile:{user_id}", expire=600)
        def get_user_profile(user_id):
            return database.get_user_profile(user_id)
    """
    return redis_cache(key_template=key_template, expire=expire)