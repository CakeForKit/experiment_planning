
import abc
import numpy.random as nr

class DistributionLaw(abc.ABC):
    @abc.abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError("Not realised method init")
    

    @abc.abstractmethod
    def get_value(self) -> float:
        raise NotImplementedError("Not realised method get_value")
    
    @abc.abstractmethod
    def sort_key(self) -> float:
        raise NotImplementedError("Not realised method sort_key")
    
class UniformDistributionLaw(DistributionLaw):
    def __init__(self, a: float, b: float) -> None:
        if not 0 <= a <= b:
            raise ValueError('The parameters should be in range [a, b]')
        self._a = a
        self._b = b

    def get_value(self) -> float:
        return nr.uniform(self._a, self._b)
    
    def sort_key(self) -> float:
        return (self._a, self._b)
    
    def info(self):
        return f"Равномерное распределение: a={self._a}, b={self._b}"

class ConstantDistributionLaw(DistributionLaw):
    def __init__(self, c: float):
        self.c = c

    def get_value(self) -> float:
        return self.c
    
    def sort_key(self) -> float:
        return self.c


if __name__ == '__main__':
    law = UniformDistributionLaw(2, 10)
    for i in range(10):
        print(law.next())
    # law = ConstantDistributionLaw(c=15)
    # print(law.random())
