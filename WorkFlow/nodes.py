from WorkFlow.base.decorators import graph_node
from WorkFlow.baseState import BaseState


@graph_node(is_default=True)
def _(state: BaseState):
    """
    空节点
    :param state:
    :return:
    """
    pass

@graph_node(is_default=True)
def continue_node(state: BaseState):
    """
    空节点
    :param state:
    :return:
    """
    pass
