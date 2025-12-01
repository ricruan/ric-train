import threading
from abc import ABCMeta

class SingletonMeta(ABCMeta):
    _instances = {}

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        # 为每个使用此元类的类创建一个独立的锁对象
        cls._class_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        # 1. 第一次检查（无锁）：如果实例已存在，直接返回，避开锁的开销
        if cls not in cls._instances:
            # 2. 获取该类独有的锁
            with cls._class_lock:
                # 3. 第二次检查（有锁）：确保线程安全，防止并发创建
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)

        return cls._instances[cls]