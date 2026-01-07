from langgraph.graph import StateGraph, START, END

from WorkFlow import graph_node_mapping
from WorkFlow.baseState import BaseState


class BaseWorkFlow:

    def __init__(self, node_list=None):
        self.node_list = node_list or []
        self.work_flow = None
        self.workflow_client = None
        self._init()

    def _init(self):
        self._init_node()
        self._init_edge()
        self.workflow_client = self.work_flow.compile()

    def _init_node(self):
        self._init_work_flow()

        # 用于记录节点基础名称出现的次数
        # 格式示例: {'say_hello': 1, 'check_data': 2}
        name_counter = {}

        # 用于存储重命名后的节点列表，最后替换 self.node_list
        rewrite_node_list = []

        # 定义一个内部辅助函数，处理单个节点的注册和重命名
        def _register_unique_node(base_name):
            # 1. 检查是否存在于映射表中
            if base_name not in graph_node_mapping:
                raise ValueError(f"Node function '{base_name}' not found in mapping.")

            # 2. 生成唯一名称
            count = name_counter.get(base_name, 0) + 1
            name_counter[base_name] = count

            # 命名策略：第一次保留原名，第二次开始加后缀 _2, _3
            # 例如: ['a', 'a'] -> ['a', 'a_2']
            unique_name = base_name if count == 1 else f"{base_name}_{count}"

            # 3. 注册节点：使用【唯一名称】作为 ID，使用【原始名称】对应的函数作为逻辑
            # 注意：LangGraph 允许不同的 Node ID 指向同一个函数对象
            self.work_flow.add_node(unique_name, graph_node_mapping[base_name])

            return unique_name

        # 遍历当前的 node_list 进行处理
        for item in self.node_list:
            if isinstance(item, str):
                # 情况 A: 单个节点字符串
                new_name = _register_unique_node(item)
                rewrite_node_list.append(new_name)

            elif isinstance(item, list):
                # 情况 B: 并行节点列表 (例如 ['say_1', 'say_1'])
                # 这里面的节点也需要处理重命名
                current_layer = []
                for sub_item in item:
                    if isinstance(sub_item, str):
                        new_name = _register_unique_node(sub_item)
                        current_layer.append(new_name)
                rewrite_node_list.append(current_layer)

        # 4. 关键步骤：更新类的 node_list
        # 这样随后的 _init_edge 方法就会使用新的唯一名称进行连线
        self.node_list = rewrite_node_list

    def _init_edge(self):
        if not self.node_list:
            return

        # 辅助函数：将单个节点字符串也包装成列表，统一处理接口
        # 例如: 'say_hello' -> ['say_hello']
        # 例如: ['a', 'b'] -> ['a', 'b']
        def to_layer(item):
            return item if isinstance(item, list) else [item]

        # 1. 处理 START -> 第一层
        # 如果第一个元素就是列表，那么 START 会连接到列表里所有的节点
        first_layer = to_layer(self.node_list[0])
        for node in first_layer:
            self.work_flow.add_edge(START, node)

        # 2. 处理中间的连线 (核心逻辑)
        # 遍历列表，连接 Current Layer -> Next Layer
        for index in range(len(self.node_list) - 1):
            current_layer = to_layer(self.node_list[index])
            next_layer = to_layer(self.node_list[index + 1])

            # 双重循环：让上一层的所有节点，连接到下一层的所有节点
            # 情况 A (一对一): ['a'] -> ['b']
            # 情况 B (发散):   ['a'] -> ['b', 'c']  (你需要的 say_bye -> list)
            # 情况 C (收束):   ['b', 'c'] -> ['d']  (你需要的 list -> say_4)
            for src_node in current_layer:
                for dst_node in next_layer:
                    self.work_flow.add_edge(src_node, dst_node)

        # 3. 处理 最后一层 -> END
        # 如果最后一个元素是列表，那么列表里所有节点都会连接到 END
        last_layer = to_layer(self.node_list[-1])
        for node in last_layer:
            self.work_flow.add_edge(node, END)


    def _init_work_flow(self):
        if not self.work_flow:
            self.work_flow = StateGraph(BaseState)

    def invoke(self, input_data: BaseState):
        self.workflow_client.invoke(input_data)


if __name__ == "__main__":
    state = BaseState(name='123')
    test = BaseWorkFlow(node_list=['say_hello', 'say_bye',['say_1','say_2','say_3'],'say_4','say_hello'])
    test.invoke(input_data=state)
    print(test.work_flow)
