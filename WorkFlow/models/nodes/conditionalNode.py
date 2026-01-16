from Base.RicUtils.dataUtils import seq_safe_get
from WorkFlow.base.enum import NodeTypeEnum
from WorkFlow.models.nodes.baseNode import BaseNode


class ConditionalNode(BaseNode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_type = NodeTypeEnum.CONDITIONAL_NODE
        if isinstance(self.node_name,tuple):
            origin_node_name = self.node_name
            self.node_name = origin_node_name[0]
            if not self.node_func:
                self.node_func = self.conditional_node_func
            if not self.end_node and seq_safe_get(origin_node_name,2):
                self.end_node = seq_safe_get(origin_node_name,2)



    @property
    def conditional_node_func(self):
        return self.conditional_node_func_mapping.get(self.conditional_params.path)

    def _register_edge(self):
        self.add_edge_plus(start_key=self.source_node, end_key=self.node_name)
        self.work_flow.add_conditional_edges(source=self.node_name, path=self.conditional_node_func,
                                        path_map=self.conditional_params.path_map or self.end_node)

    # def register_node(self):

