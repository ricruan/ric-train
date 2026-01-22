"""
WorkFlow 模块

提供工作流节点和条件的自动加载机制。
"""


from ._loader import (
    graph_node_mapping,
    base_graph_node_mapping,
    edge_condition_mapping,
    load_node,
    load_base_node,
    load_condition,
    init_base_node,
)

__all__ = [
    'graph_node_mapping',
    'base_graph_node_mapping',
    'edge_condition_mapping',
    'load_node',
    'load_base_node',
    'load_condition',
    'init_base_node',
]
