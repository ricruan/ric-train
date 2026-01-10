from WorkFlow.base.enum import NodeTypeEnum
from WorkFlow.models.nodes.baseNode import BaseNode


class ConditionalNode(BaseNode):

    def __init__(self, condition_func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_type = NodeTypeEnum.CONDITIONAL_NODE
        self.condition_func = condition_func

    def register_node(self, work_flow):
        pass