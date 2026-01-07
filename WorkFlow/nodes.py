from WorkFlow.base.decorators import graph_node
from WorkFlow.baseState import BaseState


@graph_node
def say_hello(state: BaseState):
    state.name = 'hello'
    print('hello')


@graph_node
def say_bye(state: BaseState):
    state.name = 'bye-bye'
    print('bye_bye')