from WorkFlow.baseState import BaseState
from functools import wraps


def graph_node(func):
    """
    如果节点函数忘记返回 state 会自动返回
    :param func:
    :return:
    """
    # 给函数打上标记
    func._is_graph_node = True

    @wraps(func)
    def wrapper(*args, **kwargs):
        _res = func(*args, **kwargs)

        if isinstance(_res, BaseState):
            return _res

        # 3. 在位置参数 (*args) 中查找 BaseState
        for arg in args:
            if isinstance(arg, BaseState):
                return arg

        # 4. 在关键字参数 (**kwargs) 中查找 BaseState
        for arg in kwargs.values():
            if isinstance(arg, BaseState):
                return arg

        # 5. 如果没找到（容错处理），可以选择抛出异常或返回 None
        raise ValueError(
            f"Function {func.__name__} was decorated with @graph_node but no 'BaseState' argument was passed.")

    wrapper._is_graph_node = True

    return wrapper