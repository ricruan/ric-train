import logging
from typing import Optional

from langgraph.graph import StateGraph, START, END
from operator import methodcaller

from Base.RicUtils.dataUtils import seq_safe_get
from WorkFlow import graph_node_mapping, edge_condition_mapping, base_graph_node_mapping, init_base_node
from WorkFlow.baseState import BaseState
from WorkFlow.exception import WorkFlowBaseException
from WorkFlow.models.nodes.baseNode import BaseNode
from WorkFlow.models.nodes.nodeFactory import NodeFactory

logger = logging.getLogger(__name__)

class BaseWorkFlow:

    def __init__(self, node_list=None):
        self.node_list = node_list or []
        self.work_flow: Optional[StateGraph] = None
        self.workflow_client = None
        self.node_instances = []
        # ____________________
        self._init()



    def _init(self):
        self._init_work_flow()
        node_instance = NodeFactory.nodelist_2_node(self.node_list,graph_node_mapping)
        for i in node_instance:
            i.register_node(self.work_flow)
        self.workflow_client = self.work_flow.compile()


    def _init_work_flow(self):
        if not self.work_flow:
            self.work_flow = StateGraph(BaseState)

    def invoke(self, input_data: BaseState):
        self.workflow_client.invoke(input_data)


if __name__ == "__main__":
    state = BaseState(name='123')
    test = BaseWorkFlow(node_list=['say_hello', ('say_bye','early_stop'),['say_1','say_2','say_3'],['say_2','say_3'],'say_4','say_hello'])
    # test1 = NodeFactory.nodelist_2_node(['say_hello', ('say_bye','early_stop'),['say_1','say_2','say_3'],['say_2','say_3'],'say_4','say_hello'],graph_node_mapping)
    print(test)
    # test.invoke(input_data=state)
