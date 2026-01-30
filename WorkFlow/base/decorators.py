import copy

from Base.RicUtils.dataUtils import calculate_diff_dict
from WorkFlow.base.baseState import BaseState
from functools import wraps


def graph_node(func=None, *,is_default: bool = False):
    """
    如果节点函数忘记返回 修改内容,Here 会自动对比差异并返回差异部分进行更新
    :param func:
    :param is_default: 是否为需要初始化的基础默认节点
    :return:
    """
    if func is None:
        # 这是一个带参调用的工厂：@graph_node(is_default=True)
        return lambda f: graph_node(f, is_default=is_default)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise Exception(f"节点函数执行失败:{func.__name__}") from e

    wrapper._is_graph_node = True
    wrapper._is_default = is_default
    return wrapper


def edge_condition(func):
    func._is_edge_condition = True

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper._is_edge_condition = True
    return wrapper
