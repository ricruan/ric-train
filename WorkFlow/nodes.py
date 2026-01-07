from WorkFlow.base.decorators import graph_node
from WorkFlow.baseState import BaseState


@graph_node
def none_node(state: BaseState):
    """
    空节点
    :param state:
    :return:
    """
    pass
