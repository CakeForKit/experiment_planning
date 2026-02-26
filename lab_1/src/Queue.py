
# LIFO
class Queue:
    def __init__(self):
        self.queue = [] 

    # время прихода
    def add(self, time: float) -> None:
        self.queue.append(time)
        self.queue.sort(reverse=True)
    
    def first(self) -> float:
        return self.queue[0]
    
    def pop(self) -> float:
        return self.queue.pop(0)

    def empty(self) -> bool:
        return len(self.queue) == 0
    
    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"Queue({self.queue[:10]})"
    
