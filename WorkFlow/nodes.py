from WorkFlow.base.decorators import graph_node
from WorkFlow.base.baseState import BaseState
from typing import TypeVar

T = TypeVar('T', bound=BaseState)

@graph_node(is_default=True)
def _(state: T):
    """
    空节点
    :param state:
    :return:
    """
    pass

@graph_node(is_default=True)
def continue_node(state: T):
    """
    空节点
    :param state:
    :return:
    """
    pass
