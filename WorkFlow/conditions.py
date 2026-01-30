from WorkFlow.base.decorators import edge_condition
from WorkFlow.base.baseState import BaseState
from langgraph.graph import END

@edge_condition
def early_stop(state: BaseState):
    """
    早停条件
    :param state:
    :return:
    """
    if state.early_stop_flag:
        return END
    else:
        return "continue_node"
