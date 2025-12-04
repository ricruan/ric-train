import threading
from abc import ABCMeta

class SingletonMeta(ABCMeta):
    _instances = {}

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls._class_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in SingletonMeta._instances:
            with cls._class_lock:
                if cls not in SingletonMeta._instances:
                    instance = super().__call__(*args, **kwargs)
                    SingletonMeta._instances[cls] = instance
        return SingletonMeta._instances[cls]





if __name__ == "__main__":
    class Person(metaclass=SingletonMeta):
        def __init__(self):
            super().__init__()
            print("hello,world!")

        pass

    class Woman(Person,metaclass=SingletonMeta):
        pass

    p1 = Person()
    # p2 = Person()
    w1 = Woman()
    # print(p1 == p2)
    print(p1 == w1)
    print(bool("None" and 1))
