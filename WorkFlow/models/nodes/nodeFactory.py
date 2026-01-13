from Base.RicUtils.dataUtils import seq_safe_get
from WorkFlow.base.enum import NodeTypeEnum
from WorkFlow.models.nodes.baseNode import ConditionalParams
from WorkFlow.models.nodes.conditionalNode import ConditionalNode
from WorkFlow.models.nodes.normalNode import NormalNode
from WorkFlow.models.nodes.multiNode import MultiNode
from typing import Callable

_NODE_TYPE_MAP = {
    list: MultiNode,
    str: NormalNode,
    tuple: ConditionalNode,
}


class NodeFactory:

    @staticmethod
    def create_node(data, last_item, next_item, node_func, conditional_param=None):
        node_class = _NODE_TYPE_MAP.get(type(data))
        if node_class is None:
            raise TypeError(f"Unsupported data type: {type(data)}")

        # 构建通用参数
        kwargs = {
            'current_node': data,
            'last_node': last_item,
            'next_node': next_item,
            'node_func': node_func,
        }

        # 如果是 ConditionalNode，额外传入 conditional_params
        if node_class is ConditionalNode:
            kwargs['conditional_params'] = conditional_param

        return node_class(**kwargs)

    @staticmethod
    def nodelist_2_node(simple_nodes: list, node_func_mapping: dict):
        i = 0
        nodes = []
        for node in simple_nodes:
            current = NodeFactory._node_handle(node)
            last_item = seq_safe_get(simple_nodes, i-1)
            next_item = seq_safe_get(simple_nodes, i+1)
            nodes.append(NodeFactory.create_node(current, last_item, next_item, node_func_mapping.get(current)))
            i += 1
        return nodes

    @staticmethod
    def _node_handle(node):
        if isinstance(node,str):
            return node
        elif isinstance(node,list):
            return node
        elif isinstance(node,tuple):
            return node[0]
        else:
            raise TypeError(f"Unsupported data type: {type(node)}")



if __name__ == '__main__':
    def _test():
        print('test')


    _data = 'test'
    _last_item = None
    _next_item = 'next'
    _node_func = _test
    _conditional_param = ConditionalParams(path='path', path_map={'a': 'b'})
    _node = NodeFactory.create_node(_data, _last_item, _next_item, _node_func, _conditional_param)
    print(_node)
