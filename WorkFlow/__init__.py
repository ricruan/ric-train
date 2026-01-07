from . import nodes
import os

# 禁用LangChain自动追踪以避免UUID警告
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
from Base.RicUtils.reflectUtils import get_sign_func_from_module

graph_node_mapping = get_sign_func_from_module(sign='_is_graph_node', module=nodes)