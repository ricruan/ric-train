from dataclasses import dataclass
from typing import Any, Optional, Callable

from WorkFlow.base.enum import NodeTypeEnum
from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, START, END

from WorkFlow.exception import WorkFlowBaseException


@dataclass
class ConditionalParams:
    """
    条件参数
    """
    path: Any
    path_map: dict | list


class BaseNode(ABC):

    def __init__(self,
                 current_node: str | list[str],
                 node_func: Callable | str,
                 last_node: str | list[str] = '',
                 next_node: str | list[str] = '',
                 conditional_params: Optional[ConditionalParams] = None,
                 node_func_mapping: dict = None,
                 node_type: NodeTypeEnum = NodeTypeEnum.NORMAL_NODE):
        """
        :param current_node: 当前节点名称
        :param node_func: 当前节点函数
        :param last_node: last节点名称
        :param next_node: next节点名称
        :param conditional_params: 条件参数，条件Node时使用
        :param node_func_mapping: 节点函数映射字典
        :param node_type: 节点类型
        """
        self.node_name = current_node
        self.node_func = node_func
        self.source_node = last_node
        self.end_node = next_node
        self.conditional_params = conditional_params
        self.node_func_mapping = node_func_mapping or {}
        self.node_type = node_type

    @property
    def callable_node_func(self):
        if isinstance(self.node_func,str):
            return self.node_func_mapping.get(self.node_func)
        else:
            return self.node_func


    def _register_edge(self, work_flow: StateGraph):
        """
        底层是set() 重复注册无所谓
        :param work_flow:
        :return:
        """
        self.add_edge_plus(work_flow=work_flow, start_key=self.source_node, end_key=self.end_node)

    def register_node(self, work_flow: StateGraph):
        """
        注册节点
        :param work_flow: 工作流
        :return:
        """
        if self.node_type == NodeTypeEnum.NORMAL_NODE:
            self.add_node_plus(work_flow=work_flow, node_name=self.node_name, node_func=self.callable_node_func)
        elif self.node_type == NodeTypeEnum.MULTI_NODE:
            for i in self.node_name:
                self.add_node_plus(work_flow=work_flow, node_name=i, node_func=self.node_func_mapping.get(i))

    def register_edge(self, work_flow: StateGraph):
        """
        注册边
        :param work_flow: 工作流
        :return:
        """
        self.register_node(work_flow=work_flow)
        if not self.source_node:
            work_flow.add_edge(start_key=START, end_key=self.node_name)

        if not self.end_node:
            work_flow.add_edge(start_key=self.node_name, end_key=END)

        if self.source_node and self.end_node:
            self._register_edge(work_flow=work_flow)

    def run(self):
        try:
            self.node_func()
        except Exception as e:
            raise WorkFlowBaseException(f"执行节点 {self.node_name} 时发生异常：{e}")

    @staticmethod
    def add_edge_plus(work_flow: StateGraph, start_key: str | list[str], end_key: str | list[str]):
        """
        添加边
        :param work_flow: 工作流
        :param start_key: 起始节点
        :param end_key: 结束节点
        :return:
        """
        start_key = [start_key] if isinstance(start_key, str) else start_key
        end_key = [end_key] if isinstance(end_key, str) else end_key

        for start in start_key:
            for end in end_key:
                work_flow.add_edge(start_key=start, end_key=end)

    @staticmethod
    def add_node_plus(work_flow: StateGraph, node_name: str, node_func):
        if node_name in work_flow.nodes:
            return
        work_flow.add_node(node_name, node_func)
