from WorkFlow.base.decorators import graph_node
from WorkFlow.base.baseState import BaseState



@graph_node
def say_hello(state: BaseState):
    state.name = 'hello'
    print('hello')


@graph_node
def say_bye(state: BaseState):
    state.name = 'bye-bye'
    # state.early_stop_flag = True
    print('bye_bye')

@graph_node
def say_1(state: BaseState):
    state.ric_id = 'say_1'
    print("12323231 v111111")

@graph_node
def say_2(state: BaseState):
    return {'name': 'say_2'}

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