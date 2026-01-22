import logging
from typing import Optional

from langgraph.graph import StateGraph
from WorkFlow import graph_node_mapping, edge_condition_mapping
from WorkFlow.baseState import BaseState
from WorkFlow.models.nodes.nodeFactory import NodeFactory

logger = logging.getLogger(__name__)

class BaseWorkFlow:

    def __init__(self, node_list=None):
        self.node_list = node_list or []
        self.work_flow: Optional[StateGraph] = None
        self.workflow_client = None
        self.node_instances = []
        self.node_mapping: dict = {**graph_node_mapping}
        # ____________________
        self._node_list_check()
        self._init()

    def _node_list_check(self):
        def _unique_name(name: str, _registered_node: list[str]) -> str:
            """生成不重复的节点名"""
            if name not in _registered_node:
                _registered_node.append(name)
                return name

            idx = 1
            while True:
                new_name = f"{name}_{idx}"
                if new_name not in _registered_node:
                    _registered_node.append(new_name)
                    return new_name
                idx += 1

        def _register(name: str) -> str:
            """
            生成唯一名称 + 建立新旧映射
            """
            new = _unique_name(name, registered_node)
            # 关键：新名称映射到旧函数
            self.node_mapping[new] = self.node_mapping.get(name)
            return new

        tem_node_list = []
        registered_node = []
        last_item = None

        for i in self.node_list:

            # ---------- list[str] ----------
            if isinstance(i, list):
                new_list = []
                for s in i:
                    if isinstance(s, str):
                        new_list.append(_register(s))
                    else:
                        new_list.append(s)
                if isinstance(last_item,list):
                    tem_node_list.append("_")
                tem_node_list.append(new_list)
            # ---------- tuple ----------
            elif isinstance(i, tuple):
                lst = list(i)

                # 第 1 个元素
                if len(lst) > 0 and isinstance(lst[0], str):
                    lst[0] = _register(lst[0])

                # 第 3 个元素
                if len(lst) > 2:
                    if isinstance(lst[2], str):
                        lst[2] = _register(lst[2])
                    elif isinstance(lst[2], list):
                        new_sub_list = []
                        for s in lst[2]:
                            if isinstance(s, str):
                                new_sub_list.append(_register(s))
                            else:
                                new_sub_list.append(s)
                        lst[2] = new_sub_list

                tem_node_list.append(tuple(lst))
            # ---------- str ----------
            elif isinstance(i, str):
                tem_node_list.append(_register(i))
            # ---------- 其他 ----------
            else:
                tem_node_list.append(i)

            last_item = i

        self.node_list = tem_node_list

    def _init(self):
        self._init_work_flow()
        node_instance = NodeFactory.nodelist_2_node(self.work_flow,self.node_list,self.node_mapping,edge_condition_mapping)
        for i in node_instance:
            i.register_edge()
        self.workflow_client = self.work_flow.compile()


    def _init_work_flow(self):
        if not self.work_flow:
            self.work_flow = StateGraph(BaseState)

    def invoke(self, input_data: BaseState):
        self.workflow_client.invoke(input_data)


if __name__ == "__main__":
    state = BaseState(name='123')
    test = BaseWorkFlow(node_list=['say_bye', ('say_bye','early_stop'),['continue_node','say_1'],['say_4','say_bye'],'say_hello'])
    # test1 = NodeFactory.nodelist_2_node(['say_hello', ('say_bye','early_stop'),['say_1','say_2','say_3'],['say_2','say_3'],'say_4','say_hello'],graph_node_mapping)
    print(test)
    test.invoke(input_data=state)
