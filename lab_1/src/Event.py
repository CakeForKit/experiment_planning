
GEN1_EVENT = 0      # "generator 1 event"
GEN2_EVENT = 1      # "generator 2 event"
COMP1_EVENT = 2     # "computer 1 event"

def type_str(type: int):
    text = ""
    if type == GEN1_EVENT:
        text = "GEN1_EVENT"
    elif type == GEN2_EVENT:
        text = "GEN2_EVENT"
    elif type == COMP1_EVENT:
        text = "COMP1_EVENT"
    else:
        text = "UNKNOWN_EVENT"
    return text

class Event:
    def __init__(self, time: float, type: str):
        self.time = time
        self.type = type

    # def nextTime(self, time) -> float:
    #     self.time = time

    def __lt__(self, other):
        if self.time == other.time:
            return self.type > other.type
        return self.time < other.time
    
    def __eq__(self, other):
        return self.time == other.time and self.type == other.type
    
    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"(type={type_str(self.type)}, time={self.time:.1f})"
    
