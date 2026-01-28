from WorkFlow.base._enum import NodeTypeEnum
from WorkFlow.models.nodes.baseNode import BaseNode


class NormalNode(BaseNode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_type = NodeTypeEnum.NORMAL_NODE
