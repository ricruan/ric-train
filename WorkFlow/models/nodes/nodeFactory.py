from multiNode import MultiNode

class NodeFactory:

    @staticmethod
    def create_by_data(data):
        if isinstance(data,list):
            return MultiNode()