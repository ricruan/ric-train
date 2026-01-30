from WorkFlow.base.wfEnum import NodeTypeEnum
from WorkFlow.models.nodes.baseNode import BaseNode


class MultiNode(BaseNode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_type = NodeTypeEnum.MULTI_NODE

