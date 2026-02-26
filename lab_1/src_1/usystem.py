import laws
from typing import List
from icecream import ic 

CLIENT_EVENT = 0    # "client_event"
OP1_EVENT = 1       # "operator 1 event"
OP2_EVENT = 2       # "operator 2 event"
OP3_EVENT = 3       # "operator 3 event"
OP4_EVENT = 4       # "operator 4 event"
COMP1_EVENT = 5     # "computer 1 event"
COMP2_EVENT = 6     # "computer 2 event"
COMP3_EVENT = 7     # "computer 3 event"

def type_str(type: int):
    text = ""
    if type == CLIENT_EVENT:
        text = "CLIENT_EVENT"
    elif type == OP1_EVENT:
        text = "OP1_EVENT"
    elif type == OP2_EVENT:
        text = "OP2_EVENT"
    elif type == OP3_EVENT:
        text = "OP3_EVENT"
    elif type == OP4_EVENT:
        text = "OP4_EVENT"
    elif type == COMP1_EVENT:
        text = "COMP1_EVENT"
    elif type == COMP2_EVENT:
        text = "COMP2_EVENT"
    elif type == COMP3_EVENT:
        text = "COMP3_EVENT"
    else:
        text = "UNKNOWN_EVENT"
    return text
    

class Event:
    def __init__(self, time: float, type: str):
        self.time = time
        self.type = type

    def nextTime(self, time):
        self.time = time

    def __lt__(self, other):
        if self.time == other.time:
            return self.type > other._type
        return self.time < other.time
    
    def __eq__(self, other):
        return self.time == other.time and self.type == other._type
    
    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"(type={type_str(self.type)}, time={self.time:.1f})"

class Queue:
    def __init__(self):
        self.queue = [] # список времени прихода

    def add(self, time: float) -> None:
        self.queue.append(time)
        self.queue.sort()
    
    def first(self) -> float:
        return self.queue[0]
    
    def pop(self) -> float:
        return self.queue.pop(0)

    def empty(self) -> bool:
        return len(self.queue) == 0

class Operator:
    def __init__(self, distributionLaw: laws.DistributionLaw, type_event: int):
        self.distributionLaw = distributionLaw
        self.type_event = type_event
        self.end_work_time = 0.0

    def start_work(self, timeStart) -> float:
        if self.is_busy(timeStart):
            raise Exception("try to start work - operator is busy!")
        self.end_work_time = timeStart + self.distributionLaw.get_value()
        return self.end_work_time

    def is_busy(self, timeCheck) -> bool:
        return self.end_work_time >= timeCheck
    
    def sort_key(self) -> float:
        return self.distributionLaw.sort_key()
    
class Computer:
    def __init__(self, distributionLaw: laws.DistributionLaw, type_event: int):
        self.distributionLaw = distributionLaw
        self.type_event = type_event
        self.end_work_time = 0.0

    def start_work(self, timeStart) -> float:
        if self.is_busy(timeStart):
            raise Exception("try to start work - computer is busy!")
        self.end_work_time = timeStart + self.distributionLaw.get_value()
        return self.end_work_time

    def is_busy(self, timeCheck) -> bool:
        return self.end_work_time > timeCheck

class System:
    def __init__(
            self, clientLaw: laws.DistributionLaw,
            operators: List[Operator],
            computer1: Computer, computer2: Computer, computer3: Computer,
            NprocClients: int,
    ):
        self.clientLaw = clientLaw  
        self.operators = operators  
        self.computer1 = computer1
        self.computer2 = computer2
        self.computer3 = computer3
        self.NprocClients = NprocClients
        self.queue1 = Queue()
        self.queue2 = Queue()

        self.waiting_queue1 = []
        self.waiting_queue2 = []

    def simulate(self):
        self.events_list = [
            Event(self.clientLaw.get_value(), CLIENT_EVENT),
        ]
        self.generated_count = 0
        self.processed_count = 0
        self.rejected_count = 0
        self.waiting_queue1 = []
        self.waiting_queue2 = []

        while self.processed_count < self.NprocClients:
            event = self.events_list.pop(0)
            self.process_event(event)

    def process_event(self, event):
        if event.type == CLIENT_EVENT:
            self.generated_count += 1

            workStarted = False
            for op in sorted(self.operators, key=lambda x: x.sort_key()):
                if not op.is_busy(event.time):
                    end_work_time = op.start_work(event.time)
                    self.events_list.append(Event(end_work_time, op.type_event))
                    workStarted = True
                    break
            if not workStarted:
                self.rejected_count += 1

            self.events_list.append(Event(event.time + self.clientLaw.get_value(), CLIENT_EVENT))
        
        elif event.type == OP1_EVENT or event.type == OP2_EVENT or event.type == OP3_EVENT:
            self.queue1.add(event.time)
            if not self.computer1.is_busy(self.queue1.first()):
                self.waiting_queue1.append(0)
                end_work_time = self.computer1.start_work(self.queue1.pop())
                self.events_list.append(Event(end_work_time, self.computer1.type_event))

        elif event.type == OP4_EVENT:
            self.queue2.add(event.time)
            if not self.computer2.is_busy(self.queue2.first()):
                self.waiting_queue2.append(0)
                end_work_time = self.computer2.start_work(self.queue2.pop())
                self.events_list.append(Event(end_work_time, self.computer2.type_event))

        elif event.type == COMP1_EVENT:
            self.processed_count += 1
            if not self.queue1.empty():
                in_queue_event = self.queue1.pop()
                start_work_time = max(in_queue_event, event.time)
                self.waiting_queue1.append(start_work_time - in_queue_event)
                end_work_time = self.computer1.start_work(start_work_time)
                self.events_list.append(Event(end_work_time, self.computer1.type_event))

        elif event.type == COMP2_EVENT:
            self.processed_count += 1
            if not self.queue2.empty():
                in_queue_event = self.queue2.pop()
                start_work_time = max(in_queue_event, event.time)
                self.waiting_queue2.append(start_work_time - in_queue_event)
                end_work_time = self.computer2.start_work(start_work_time)
                self.events_list.append(Event(end_work_time, self.computer2.type_event))

        elif event.type == COMP3_EVENT:
            self.processed_count += 1
            if not self.queue2.empty():
                in_queue_event = self.queue2.pop()
                start_work_time = max(in_queue_event, event.time)
                self.waiting_queue2.append(start_work_time - in_queue_event)
                end_work_time = self.computer3.start_work(start_work_time)
                self.events_list.append(Event(end_work_time, self.computer3.type_event))
        else:
            raise Exception("UNKNOWN_EVENT")
        self.events_list.sort()
        # print(self.events_list)

    def avg_time_waiting_queue1(self) -> float:
        # print(self.waiting_queue1)
        if len(self.waiting_queue1) == 0:
            return 0
        return sum(self.waiting_queue1) / len(self.waiting_queue1)
    
    def avg_time_waiting_queue2(self) -> float:
        # print(self.waiting_queue1)
        if len(self.waiting_queue2) == 0:
            return 0
        return sum(self.waiting_queue2) / len(self.waiting_queue2)

if __name__ == '__main__':
    clientLaw = laws.UniformDistributionLaw(5, 9)
    operators = [
        Operator(laws.UniformDistributionLaw(15, 25), OP1_EVENT),
        Operator(laws.UniformDistributionLaw(20, 40), OP2_EVENT),
        Operator(laws.UniformDistributionLaw(30, 60), OP3_EVENT),
        Operator(laws.UniformDistributionLaw(10, 20), OP4_EVENT),
    ]
    computer1 = Computer(laws.ConstantDistributionLaw(20), COMP1_EVENT)
    computer2 = Computer(laws.ConstantDistributionLaw(20), COMP2_EVENT)
    computer3 = Computer(laws.ConstantDistributionLaw(15), COMP3_EVENT)
    N = 300
    system = System(clientLaw, operators, computer1, computer2, computer3, N)

    system.simulate()
    print(f"generated_count = {system.generated_count}\n")
    print(f"processed_count = {system.processed_count}\n")
    print(f"rejected_count = {system.rejected_count}\n")
    p = system.rejected_count / (system.processed_count + system.rejected_count)
    print(f"p = {p}\n")
    print(f"avg_time_waiting_queue1 = {system.avg_time_waiting_queue1()}")
    print(f"avg_time_waiting_queue2 = {system.avg_time_waiting_queue2()}")
