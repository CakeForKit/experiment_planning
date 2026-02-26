
import abc
import numpy.random as nr
import math

class DistributionLaw(abc.ABC):
    @abc.abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError("Not realised method init")
    

    @abc.abstractmethod
    def get_value(self) -> float:
        raise NotImplementedError("Not realised method get_value")
    
    @abc.abstractmethod
    def get_intensity(self) -> float:
        raise NotImplementedError("Not realised method get_value")
    
    # @abc.abstractmethod
    # def sort_key(self) -> float:
    #     raise NotImplementedError("Not realised method sort_key")
    
class RayleighDistributionLaw(DistributionLaw):
    # def __init__(self, intensity: float):
    #     self.sigma = (1/intensity) * math.sqrt(2/math.pi)

    def __init__(self, sigma: float):
        self.sigma = sigma

    def get_intensity(self) -> float:
        return 1 / (self.sigma) * math.sqrt(2/math.pi)

    def get_value(self) -> float:
        return nr.rayleigh(self.sigma)


class UniformDistributionLaw(DistributionLaw):
    # def __init__(self, middle: float, range: float) -> None:
    #     if not middle >= range:
    #         raise ValueError('The parameters should be middle >= range')
    #     self._a = middle - range
    #     self._b = middle + range

    def __init__(self, a: float, b: float) -> None:
        if not 0 <= a <= b:
            raise ValueError('The parameters should be in range [a, b]')
        self._a = a
        self._b = b

    def get_value(self) -> float:
        return nr.uniform(self._a, self._b)
    
    def get_intensity(self) -> float:
        return 2 / (self._a + self._b)
    
    # def sort_key(self) -> float:
    #     return (self._a, self._b)
    
    def info(self):
        return f"Равномерное распределение: a={self._a}, b={self._b}"



if __name__ == '__main__':
    # law = UniformDistributionLaw(2, 10)
    sigma = 10
    law = RayleighDistributionLaw(sigma)
    print(f"sigma={sigma}")
    for i in range(10):
        print(f"{law.get_value():10.2g}", end=" ")
    print()
    # law = ConstantDistributionLaw(c=15)
    # print(law.random())
