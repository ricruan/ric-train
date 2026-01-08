from WorkFlow.base.decorators import edge_condition
from WorkFlow.baseState import BaseState
from langgraph.graph import END

@edge_condition
def early_stop(state: BaseState):
    if state.early_stop_flag:
        return END
    else:
        return "continue_node"
