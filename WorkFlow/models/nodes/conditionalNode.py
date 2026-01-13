from WorkFlow.base.enum import NodeTypeEnum
from WorkFlow.models.nodes.baseNode import BaseNode


class ConditionalNode(BaseNode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_type = NodeTypeEnum.CONDITIONAL_NODE

    def _register_edge(self, work_flow):
        work_flow.add_conditional_edges(source=self.node_name, path=self.conditional_params.path,
                                        path_map=self.conditional_params.path_map)
