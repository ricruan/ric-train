from WorkFlow.base.enum import NodeTypeEnum
from abc import ABC, abstractmethod
from langgraph.graph import StateGraph

class BaseNode(ABC):

    def __init__(self,):
        self.node_type = NodeTypeEnum.NORMAL_NODE


    @abstractmethod
    def register_node(self,work_flow: StateGraph):
        pass