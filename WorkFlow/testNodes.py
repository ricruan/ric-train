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

@graph_node
def say_1(state: BaseState):
    print("12323231 v111111")

@graph_node
def say_2(state: BaseState):
    print(2)

@graph_node
def say_3(state: BaseState):
    print(3)

@graph_node
def say_4(state: BaseState):
    print(4)

@graph_node
def say_5(state: BaseState):
    print(5)

@graph_node
def say_6(state: BaseState):
    print(6)