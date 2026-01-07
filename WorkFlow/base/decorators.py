import copy

from Base.RicUtils.dataUtils import calculate_diff_dict
from WorkFlow.baseState import BaseState
from functools import wraps


def graph_node(func):
    """
    如果节点函数忘记返回 修改内容,Here 会自动对比差异并返回差异部分进行更新
    :param func:
    :return:
    """
    # 给函数打上标记
    func._is_graph_node = True

    @wraps(func)
    def wrapper(*args, **kwargs):
        _origin_state = BaseState.find_me(*args, **kwargs)
        if _origin_state:
            _origin_state = copy.deepcopy(_origin_state)

        _res = func(*args, **kwargs)

        if _res:
            return _res

        _new_state = BaseState.find_me(*args, **kwargs)
        return calculate_diff_dict(old_data=dict(_origin_state),new_data=dict(_new_state))



    wrapper._is_graph_node = True

    return wrapper