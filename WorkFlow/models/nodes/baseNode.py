import re
from dataclasses import dataclass
from typing import Any, Optional, Callable

from Base.RicUtils.dataUtils import remove_none
from WorkFlow.base.wfEnum import NodeTypeEnum
from abc import ABC
from langgraph.graph import StateGraph, START, END

from WorkFlow.base.exception import WorkFlowBaseException

NodeName = str | list[str] | set[str] | tuple[str, ...]

@dataclass
class ConditionalParams:
    """
    条件参数
    """
    path: Any
    path_map: dict | list


class BaseNode(ABC):

    def __init__(self,
                 current_node: NodeName,
                 node_func: Callable = None,
                 last_node: NodeName = '',
                 next_node: NodeName = '',
                 conditional_params: Optional[ConditionalParams] = None,
                 node_func_mapping: dict = None,
                 conditional_node_func_mapping: dict = None,
                 node_type: NodeTypeEnum = NodeTypeEnum.NORMAL_NODE,
                 work_flow: StateGraph = None):
        """
        :param current_node: 当前节点名称
        :param node_func: 当前节点函数
        :param last_node: last节点名称
        :param next_node: next节点名称
        :param conditional_params: 条件参数，条件Node时使用
        :param node_func_mapping: 节点函数映射字典
        :param conditional_node_func_mapping: 条件节点Path函数映射字典
        :param node_type: 节点类型
        :param work_flow: 工作流对象
        """
        self.node_name = current_node
        self.node_func = node_func
        self.source_node = last_node
        self.end_node = next_node
        self.conditional_params = conditional_params
        self.node_func_mapping = node_func_mapping or {}
        self.conditional_node_func_mapping = conditional_node_func_mapping or {}
        self.node_type = node_type
        self.work_flow = work_flow

    def get_callable_node_func(self, node: str):
        res = self.node_func_mapping.get(node)
        if not res:
            # 下划线数字后缀
            res = self.node_func_mapping.get(re.sub(r'_[0-9]+$', '', node))
        if not res:
            raise WorkFlowBaseException(f"Node:{node} 获取节点函数获取失败")
        return res

    def _register_edge(self):
        """
        底层是set() 重复注册无所谓
        :return:
        """
        self.add_edge_plus(start_key=self.source_node, end_key=self.node_name)
        self.add_edge_plus(start_key=self.node_name, end_key=self.end_node)

    @staticmethod
    def _node_2_list(node: NodeName):
        if isinstance(node, tuple) or not node:
            return []
        if isinstance(node, str):
            return [node]
        return node

    def register_node(self):
        """
        注册节点
        :return:
        """
        _source = self._node_2_list(self.source_node)
        _end = self._node_2_list(self.end_node)
        _cur = self._node_2_list(self.node_name)
        l1 = remove_none(set(_source + _cur))
        l2 = remove_none(set(_end + _cur))
        self.add_node_plus(node_name=l1)
        self.add_node_plus(node_name=l2)

    def register_edge(self):
        """
        注册边
        :return:
        """
        self.register_node()
        if not self.source_node:
            self.add_edge_plus(start_key=START, end_key=self.node_name)

        if not self.end_node:
            self.add_edge_plus(start_key=self.node_name, end_key=END)

        if self.source_node and self.end_node:
            self._register_edge()

    def run(self):
        try:
            self.node_func()
        except Exception as e:
            raise WorkFlowBaseException(f"执行节点 {self.node_name} 时发生异常：{e}")

    def add_edge_plus(self, start_key: NodeName, end_key: NodeName):
        """
        添加边
        :param start_key: 起始节点
        :param end_key: 结束节点
        :return:
        """
        start_key = self._node_2_list(start_key)
        end_key = self._node_2_list(end_key)

        for start in start_key:
            for end in end_key:
                self.work_flow.add_edge(start_key=start, end_key=end)

    def add_node_plus(self, node_name: NodeName):

        if isinstance(node_name, list) or isinstance(node_name, set):
            for i in node_name:
                self.add_node_plus(node_name=i)
            return
        if isinstance(node_name, str):
            if node_name in self.work_flow.nodes:
                return
            self.work_flow.add_node(node_name, self.get_callable_node_func(node_name))
