from WorkFlow.base.decorators import edge_condition
from WorkFlow.baseState import BaseState


@edge_condition
def early_stop(state: BaseState):
    if state.early_stop_flag:
        return "__end__"
    else:
        return "continue_node"
