from WorkFlow.base.enum import NodeTypeEnum
from WorkFlow.models.nodes.baseNode import ConditionalParams
from WorkFlow.models.nodes.conditionalNode import ConditionalNode
from WorkFlow.models.nodes.normalNode import NormalNode
from WorkFlow.models.nodes.multiNode import MultiNode

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
    def list_2_node(simple_nodes: list):
        last_item = None
        next_item = None
        i = 0
        for node in simple_nodes:
            pass
        pass



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