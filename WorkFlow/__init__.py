"""
WorkFlow 模块

提供工作流节点和条件的自动加载机制。
"""

from .base.baseWorkFlow import BaseWorkFlow
from ._loader import (
    load_node,
    load_condition,
)

__all__ = [
    'load_node',
    'load_condition',
    'BaseWorkFlow'
]
