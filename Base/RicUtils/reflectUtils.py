import inspect


def get_sign_func_from_module(sign: str,module):
    """
    从模块中遍历所有函数，获取 带有指定标记 的函数
    返回 函数名 和 函数对象 的键值对 dict
    """
    result = {}
    for name, obj in inspect.getmembers(module):
        # 检查是否是函数，并且有 _is_ric_decorated 标记
        if inspect.isfunction(obj) and getattr(obj, sign, False):
            result[name] = obj

    return result
