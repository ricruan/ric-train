from WorkFlow.base.decorators import graph_node
from WorkFlow.baseState import BaseState


@graph_node
def _(state: BaseState):
    """
    空节点
    :param state:
    :return:
    """
    pass

@graph_node
def continue_node(state: BaseState):
    """
    空节点
    :param state:
    :return:
    """
    pass
