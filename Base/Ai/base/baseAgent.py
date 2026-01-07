from abc import abstractmethod, ABC


class BaseAgent(ABC):


    @abstractmethod
    def chat(self):
        pass