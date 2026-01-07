from . import testNodes
from . import nodes

from Base.RicUtils.reflectUtils import get_sign_func_from_module

graph_node_mapping = {}

def load_node(module):
    global graph_node_mapping
    _res = get_sign_func_from_module(sign='_is_graph_node', module=module)
    graph_node_mapping = {**graph_node_mapping,**_res}


load_node(testNodes)
load_node(nodes)