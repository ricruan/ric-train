from langgraph.graph import StateGraph
from . import testNodes
from . import nodes
from . import conditions

from Base.RicUtils.reflectUtils import get_sign_func_from_module

graph_node_mapping = {}
base_graph_node_mapping = {}
edge_condition_mapping = {}


def load_node(module, mapping_dict: dict):
    """
    Load Node from module ~
    :param mapping_dict:
    :param module:
    :return:
    """
    load_base_node(module,base_graph_node_mapping)
    _res = get_sign_func_from_module(sign='_is_graph_node', module=module)
    mapping_dict.update(_res)


def load_base_node(module, mapping_dict: dict):
    """
    Load Base Node from module ~
    :param mapping_dict:
    :param module:
    :return:
    """
    _res = get_sign_func_from_module(sign='_is_default', module=module)
    mapping_dict.update(_res)


def init_base_node(work_flow: StateGraph):
    for k, v in base_graph_node_mapping.items():
        work_flow.add_node(k, v)


def load_condition(module,mapping_dict: dict):
    _res = get_sign_func_from_module(sign='_is_edge_condition', module=module)
    mapping_dict.update(_res)


load_node(testNodes, graph_node_mapping)
load_node(nodes, graph_node_mapping)
load_condition(conditions, edge_condition_mapping)