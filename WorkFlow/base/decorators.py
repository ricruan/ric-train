

def graph_node(func):
    # 给函数打上标记
    func._is_graph_node = True
    return func