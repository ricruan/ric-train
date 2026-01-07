from langgraph.graph import StateGraph, START, END

from WorkFlow import graph_node_mapping
from WorkFlow.baseState import BaseState


class BaseWorkFlow:

    def __init__(self, node_list=None):
        self.node_list = node_list or []
        self.work_flow = None
        self.workflow_client = None
        self._init()

    def _init(self):
        self._init_node()
        self._init_edge()
        self.workflow_client = self.work_flow.compile()

    def _init_node(self):
        self._init_work_flow()

        for i in set(self.node_list):
            if isinstance(i, str):
                self.work_flow.add_node(i, graph_node_mapping[i])

    def _init_edge(self):
        if not self.node_list:
            return
        self.work_flow.add_edge(START, self.node_list[0])
        self.work_flow.add_edge(self.node_list[-1], END)
        for i in self.node_list[:-1]:
            self.work_flow.add_edge(i, self.node_list[self.node_list.index(i) + 1])

    def _init_work_flow(self):
        if not self.work_flow:
            self.work_flow = StateGraph(BaseState)

    def invoke(self, input_data: BaseState):
        self.workflow_client.invoke(input_data)


if __name__ == "__main__":
    state = BaseState(name='123')
    test = BaseWorkFlow(node_list=['say_hello', 'say_bye'])
    test.invoke(input_data=state)
    print(test.work_flow)
