"""
工作流节点和条件的自动加载机制

提供加载自定义节点、基础节点和边条件的功能。
"""

from typing import Dict, Callable, Any
from langgraph.graph import StateGraph

from . import testNodes
from . import nodes
from . import conditions
from Base.RicUtils.reflectUtils import get_sign_func_from_module


# =========================
# 全局映射字典
# =========================
graph_node_mapping: Dict[str, Callable] = {}
"""自定义图节点映射字典"""

base_graph_node_mapping: Dict[str, Callable] = {}
"""基础图节点映射字典"""

edge_condition_mapping: Dict[str, Callable] = {}
"""边条件映射字典"""


# =========================
# 节点加载函数
# =========================

def load_node(module: Any, mapping_dict: Dict[str, Callable]) -> None:
    """
    从模块自动加载带@graph_node装饰器的函数作为图节点
    ./base/decorators.py
    同时加载基础节点（标记为 _is_default）和自定义节点（标记为 _is_graph_node）。

    Args:
        module: 要加载节点的模块
        mapping_dict: 节点映射字典，用于存储加载的节点

    """
    load_base_node(module, base_graph_node_mapping)
    _res = get_sign_func_from_module(sign='_is_graph_node', module=module)
    mapping_dict.update(_res)


def load_base_node(module: Any, mapping_dict: Dict[str, Callable]) -> None:
    """
    从模块加载基础节点

    仅加载标记为 _is_default 的节点。

    Args:
        module: 要加载基础节点的模块
        mapping_dict: 基础节点映射字典，用于存储加载的节点

    """
    _res = get_sign_func_from_module(sign='_is_default', module=module)
    mapping_dict.update(_res)


# =========================
# 条件加载函数
# =========================

def load_condition(module: Any, mapping_dict: Dict[str, Callable]) -> None:
    """
    从模块自动加载带@edge_condition装饰器的函数作为边条件
    ./base/decorators.py
    加载标记为 _is_edge_condition 的条件函数。

    Args:
        module: 要加载条件的模块
        mapping_dict: 条件映射字典，用于存储加载的条件

    """
    _res = get_sign_func_from_module(sign='_is_edge_condition', module=module)
    mapping_dict.update(_res)





# =========================
# 初始化自动加载
# =========================

# 在模块加载时自动加载测试节点、自定义节点和条件
load_node(testNodes, graph_node_mapping)
load_node(nodes, graph_node_mapping)
load_condition(conditions, edge_condition_mapping)
