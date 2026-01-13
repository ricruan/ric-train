import logging
from typing import Optional

from langgraph.graph import StateGraph, START, END

from Base.RicUtils.dataUtils import seq_safe_get
from WorkFlow import graph_node_mapping, edge_condition_mapping, base_graph_node_mapping, init_base_node
from WorkFlow.baseState import BaseState
from WorkFlow.exception import WorkFlowBaseException
from WorkFlow.models.nodes.baseNode import BaseNode

logger = logging.getLogger(__name__)

class BaseWorkFlow:

    def __init__(self, node_list=None):
        self._node_list = node_list or []
        self.work_flow: Optional[StateGraph] = None
        self.workflow_client = None
        # ____________________
        self._init()


    @property
    def node_list(self):
        return self._node_list

    @node_list.setter
    def node_list(self, value):
        self._node_list = value
        self._check_node_list()



    def add_node(self,node_name: str,node):
        """
        封装一下，避免重复注册
        :param node_name:
        :param node:
        :return:
        """
        if node_name in self.work_flow.nodes:
            return
        self.work_flow.add_node(node_name,node)

    def add_conditional_edges(self,source,path,path_map = None):
        self.work_flow.add_conditional_edges(source=source,path=path,path_map=path_map)


    def _check_node_list(self):
        """
        检查 node list 的合理性
        :return:
        """
        index = 0
        for i in self.node_list[:-1]:
            _next = self.node_list[index + 1]
            # 连续两个list节点之间穿插一个空节点
            if isinstance(i,list) and isinstance(_next,list):
                self.node_list.insert(index+1,'_')
                index += 1
            # conditional_edge tuple 如果下一层节点和map不一致，自动拓展一层
            if isinstance(i,tuple):
                _map = seq_safe_get(i,2)
                if not _map:
                    tmp = list(i)
                    tem_next = [_next] if isinstance(_next,str) else _next
                    tmp.append({item:item for item in tem_next})
                    self.node_list[index] = tuple(tmp)
                if _map and isinstance(_map,dict) and set(_map.values()) != set(_next):
                    self.node_list.insert(index+1,list(_map.values()) )
                    index += 1
            index += 1

    def _init(self):
        self._init_node()
        self._init_edge()
        self.workflow_client = self.work_flow.compile()


    def _init_node(self):
        self._init_work_flow()
        init_base_node(self.work_flow)
        self._check_node_list()
        # 用于记录节点基础名称出现的次数
        # 格式示例: {'say_hello': 1, 'check_data': 2}
        name_counter = {}

        # 用于存储重命名后的节点列表，最后替换 self.node_list
        rewrite_node_list = []

        # 定义一个内部辅助函数，处理单个节点的注册和重命名
        def _register_unique_node(base_name,soft_register: bool = False):
            # 1. 检查是否存在于映射表中
            if base_name not in graph_node_mapping:
                raise ValueError(f"Node function '{base_name}' not found in mapping.")

            # 2. 生成唯一名称
            count = name_counter.get(base_name, 0) + 1
            name_counter[base_name] = count

            # 软注册， 如果发现已经有注册的了 就不注册了
            if soft_register and count > 1:
                return None

            # 命名策略：第一次保留原名，第二次开始加后缀 _2, _3
            # 例如: ['a', 'a'] -> ['a', 'a_2']
            unique_name = base_name if count == 1 else f"{base_name}_{count}"

            # 3. 注册节点：使用【唯一名称】作为 ID，使用【原始名称】对应的函数作为逻辑
            # 注意：LangGraph 允许不同的 Node ID 指向同一个函数对象
            self.add_node(unique_name, graph_node_mapping[base_name])

            return unique_name

        last_item = None
        # 遍历当前的 node_list 进行处理
        for item in self._node_list:
            if isinstance(item, str):
                # 情况 A: 单个节点字符串
                new_name = _register_unique_node(item) if not isinstance(last_item,tuple) else item
                rewrite_node_list.append(new_name) if new_name else None

            elif isinstance(item, list) :
                # 情况 B: 并行节点列表 (例如 ['say_1', 'say_1'])
                # 这里面的节点也需要处理重命名
                current_layer = []
                for sub_item in item:
                    if isinstance(sub_item, str):
                        new_name = _register_unique_node(sub_item) if not isinstance(last_item,tuple) else sub_item
                        current_layer.append(new_name) if new_name else None
                rewrite_node_list.append(current_layer) if current_layer else None
            elif isinstance(item, tuple) :
                need_register_node = [str(seq_safe_get(item,0))]
                item_child_nodes = seq_safe_get(item,2)
                if isinstance(item_child_nodes,dict):
                    need_register_node.extend(item_child_nodes.values())
                elif isinstance(item_child_nodes,list):
                    need_register_node.extend(item_child_nodes)
                for node in need_register_node:
                    _register_unique_node(node,soft_register=True)
                rewrite_node_list.append(item)
            last_item = item

        # 4. 关键步骤：更新类的 node_list
        # 这样随后的 _init_edge 方法就会使用新的唯一名称进行连线
        self._node_list = rewrite_node_list

    def _init_edge(self):
        if not self._node_list:
            return

        # 辅助函数：将单个节点字符串也包装成列表，统一处理接口
        # 例如: 'say_hello' -> ['say_hello']
        # 例如: ['a', 'b'] -> ['a', 'b']
        def to_layer(item):
            return item if isinstance(item, list) else [item]

        def handle_conditional_edge(current_node,next_layer_nodes):
            try:
                # TODO 完善一下
                base_list = [END]
                route_map = {**seq_safe_get(current_node, 2, {}), **{item: item for item in next_layer_nodes}}
                if isinstance(current_node, tuple):
                    self.work_flow.add_conditional_edges(
                        seq_safe_get(current_node, 0),
                        edge_condition_mapping.get(seq_safe_get(current_node, 1)),
                        base_list.extend(route_map.values())
                    )
            except Exception as e:
                raise WorkFlowBaseException("构建 Conditional Edge 时发生异常：" + str(e))

        # 1. 处理 START -> 第一层
        # 如果第一个元素就是列表，那么 START 会连接到列表里所有的节点
        first_layer = to_layer(self._node_list[0])
        for node in first_layer:
            self.work_flow.add_edge(START, node)

        # 2. 处理中间的连线 (核心逻辑)
        # 遍历列表，连接 Current Layer -> Next Layer
        for index in range(len(self._node_list) - 1):
            current_layer = to_layer(self._node_list[index])
            next_layer = to_layer(self._node_list[index + 1])

            # 双重循环：让上一层的所有节点，连接到下一层的所有节点
            # 情况 A (一对一): ['a'] -> ['b']
            # 情况 B (发散):   ['a'] -> ['b', 'c']  (你需要的 say_bye -> list)
            # 情况 C (收束):   ['b', 'c'] -> ['d']  (你需要的 list -> say_4)
            for src_node in current_layer:
                if isinstance(src_node,tuple):
                    handle_conditional_edge(src_node,next_layer)
                    continue

                for dst_node in next_layer:
                    if isinstance(dst_node, tuple):
                        self.work_flow.add_edge(src_node, dst_node[0])
                        break
                    self.work_flow.add_edge(src_node, dst_node)

        # 3. 处理 最后一层 -> END
        # 如果最后一个元素是列表，那么列表里所有节点都会连接到 END
        last_layer = to_layer(self._node_list[-1])
        for node in last_layer:
            self.work_flow.add_edge(node, END)


    def _init_work_flow(self):
        if not self.work_flow:
            self.work_flow = StateGraph(BaseState)

    def invoke(self, input_data: BaseState):
        self.workflow_client.invoke(input_data)


if __name__ == "__main__":
    state = BaseState(name='123')
    test = BaseWorkFlow(node_list=['say_hello', ('say_bye','early_stop'),['say_1','say_2','say_3'],['say_2','say_3'],'say_4','say_hello'])
    test.invoke(input_data=state)
