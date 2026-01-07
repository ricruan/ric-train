from WorkFlow.base.enum import NodeTypeEnum


class BaseNode:

    def __init__(self,node_type: NodeTypeEnum = None):
        self.node_type = node_type or NodeTypeEnum.NORMAL_NODE