import laws


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
    
