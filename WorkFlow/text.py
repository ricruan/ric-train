from WorkFlow.base.decorators import graph_node
from WorkFlow.baseState import BaseState


@graph_node
def say_hello(state: BaseState):
    print('hello')


@graph_node
def say_bye(state: BaseState):
    print('bye_bye')