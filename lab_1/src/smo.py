import heapq
import math
import numpy.random as nr

ARRIVAL = "arrival"
ARRIVAL_1 = "arrival1"
ARRIVAL_2 = "arrival2"
DEPARTURE = "departure"

def rayleigh_time(lmbd):
    if lmbd <= 0:
        lmbd = 0.0001

    scale = (1 / lmbd) / math.sqrt(math.pi / 2)
    return nr.rayleigh(scale)


def uniform_time(mean, rang):
    a = mean - rang
    b = mean + rang

    if b <= a:
        b = a + 0.0001

    return nr.uniform(a, b)


def simulate_smo(lambda1, lambda2, mu, rang, max_requests=1000):

    service_mean = 1 / mu
    total_lambda = lambda1 + lambda2
    R_calc = total_lambda / mu

    event_queue = []
    heapq.heapify(event_queue)

    current_time = 0
    last_event_time = 0
    busy_time = 0
    processed = 0

    queue = []
    server_busy = False

    wait_times = []
    system_times = []

    # первые поступления
    heapq.heappush(event_queue, (rayleigh_time(lambda1), ARRIVAL_1))
    heapq.heappush(event_queue, (rayleigh_time(lambda2), ARRIVAL_2))

    while processed < max_requests:
        current_time, event = heapq.heappop(event_queue)
        if server_busy:
            busy_time += current_time - last_event_time
        last_event_time = current_time

        if ARRIVAL in event:
            queue.append(current_time)

            if event == ARRIVAL_1:
                heapq.heappush(event_queue, (current_time + rayleigh_time(lambda1), ARRIVAL_1))
            else:
                heapq.heappush(event_queue, (current_time + rayleigh_time(lambda2), ARRIVAL_2))

            if not server_busy:
                arrival_time = queue.pop(0)

                wait_times.append(0)

                service_time = uniform_time(service_mean, rang)

                heapq.heappush(
                    event_queue,
                    (current_time + service_time, DEPARTURE)
                )

                system_times.append(service_time)
                server_busy = True

        elif event == DEPARTURE:

            processed += 1

            if queue:
                arrival_time = queue.pop(0)

                wait = current_time - arrival_time
                wait_times.append(wait)

                service_time = uniform_time(service_mean, rang)

                heapq.heappush(
                    event_queue,
                    (current_time + service_time, "departure")
                )

                system_times.append(wait + service_time)
                server_busy = True
            else:
                server_busy = False

    avg_wait = sum(wait_times) / len(wait_times)
    avg_system = sum(system_times) / len(system_times)

    R_fact = busy_time / current_time

    return R_calc, R_fact, avg_wait, avg_system, current_time
