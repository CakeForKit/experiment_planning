import laws
from Computer import Computer
from Queue import Queue
from Event import *

from typing import List

DEBUG = False

class System:
    def __init__(
            self, 
            generatorLaw1: laws.DistributionLaw, generatorLaw2: laws.DistributionLaw,
            computer1: Computer, 
            NprocClients: int,
    ):
        self.generatorLaw1 = generatorLaw1  
        self.generatorLaw2 = generatorLaw2
        self.computer1 = computer1
        self.NprocClients = NprocClients
        self.queue1 = Queue()
        self.waiting_queue1 = []

        print("Gen1 intensity = ", self.generatorLaw1.get_intensity())
        print("Gen2 intensity = ", self.generatorLaw2.get_intensity())
        print("Comp intensity = ", self.computer1.distributionLaw.get_intensity())
        self.workload_theory = self.generatorLaw1.get_intensity() / self.computer1.distributionLaw.get_intensity() + \
            self.generatorLaw2.get_intensity() / self.computer1.distributionLaw.get_intensity()
        
        self.time_modeling = 0  # время моделирования

        self.service_times = []  # список времен обслуживания

    def simulate(self):
        self.events_list = [
            Event(self.generatorLaw1.get_value(), GEN1_EVENT),
            Event(self.generatorLaw2.get_value(), GEN2_EVENT),
        ]
        self.generated_count = 2
        self.processed_count = 0
        self.waiting_queue = []

        while self.processed_count < self.NprocClients:
            self.events_list.sort()
            self.time_modeling = self.events_list[0].time
            self.process_event(self.events_list.pop(0))

    def process_event(self, event: Event):
        if DEBUG:
            print("Event: ", event)
            print("Event list: ", self.events_list)
            print(self.queue1)
            print()
            a = input()
        if event.type == GEN1_EVENT or event.type == GEN2_EVENT:
            self.generated_count += 1

            self.queue1.add(event.time)
            if not self.computer1.is_busy(self.queue1.first()):
                self.waiting_queue1.append(0)
                start_work_time = self.queue1.pop()
                end_work_time = self.computer1.start_work(start_work_time)
                self.events_list.append(Event(end_work_time, self.computer1.type_event))
                self.service_times.append(end_work_time - start_work_time)

            if event.type == GEN1_EVENT:
                self.events_list.append(Event(event.time + self.generatorLaw1.get_value(), GEN1_EVENT))
            else:
                self.events_list.append(Event(event.time + self.generatorLaw2.get_value(), GEN2_EVENT))

        elif event.type == COMP1_EVENT:
            self.processed_count += 1
            if not self.queue1.empty():
                in_queue_event = self.queue1.pop()
                start_work_time = max(in_queue_event, event.time)
                self.waiting_queue1.append(start_work_time - in_queue_event)
                end_work_time = self.computer1.start_work(start_work_time)
                self.events_list.append(Event(end_work_time, self.computer1.type_event))
                self.service_times.append(end_work_time - start_work_time)
                
        else:
            raise Exception("UNKNOWN_EVENT")
        

    def avg_time_waiting_queue1(self) -> float:
        if len(self.waiting_queue1) == 0:
            return 0
        return sum(self.waiting_queue1) / len(self.waiting_queue1)
    
    def total_time_working(self) -> float:
        return sum(self.service_times[:-1])
    

if __name__ == '__main__':
    genLaw1 = laws.RayleighDistributionLaw(sigma=1)
    genLaw2 = laws.RayleighDistributionLaw(sigma=10)
    computer1 = Computer(laws.UniformDistributionLaw(2, 10), COMP1_EVENT)
    N = 500
    system = System(generatorLaw1=genLaw1, generatorLaw2=genLaw2, computer1=computer1, NprocClients=N)

    system.simulate()
    print(f"generated_count = {system.generated_count}")
    print(f"processed_count = {system.processed_count}")
    print(f"avg_time_waiting_queue1 = {system.avg_time_waiting_queue1()}")
    print(f"time_modeling = {system.time_modeling}")
    
    print(f"workload_theory = {system.workload_theory}")
    workload_practise = system.total_time_working() / system.time_modeling
    print(f"workload_practise = {workload_practise}")
    