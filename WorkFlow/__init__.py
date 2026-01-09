from . import testNodes
from . import nodes
from . import conditions

from Base.RicUtils.reflectUtils import get_sign_func_from_module

graph_node_mapping = {}
base_graph_node_mapping = {}
edge_condition_mapping = {}

def load_node(module):
    """
    Load Node from module ~
    :param module:
    :return:
    """
    load_base_node(module)
    global graph_node_mapping
    _res = get_sign_func_from_module(sign='_is_graph_node', module=module)
    graph_node_mapping = {**graph_node_mapping,**_res}

def load_base_node(module):
    """
    Load Base Node from module ~
    :param module:
    :return:
    """
    global base_graph_node_mapping
    _res = get_sign_func_from_module(sign='_is_default', module=module)
    base_graph_node_mapping = {**base_graph_node_mapping,**_res}

def load_condition(module):
    global edge_condition_mapping
    _res = get_sign_func_from_module(sign='_is_edge_condition', module=module)
    edge_condition_mapping = {**edge_condition_mapping,**_res}

load_node(testNodes)
load_node(nodes)
load_condition(conditions)