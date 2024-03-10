import time as t
from dataclasses import dataclass


@dataclass
class _Simulate:
    simulating: bool = False
    start_time: float = t.time()
    starting_time: float = t.time()
    speed: float = 1


simulating = _Simulate()


def simulate(start_time: float = t.time(), speed: float = 1) -> None:
    simulating.simulating = True
    simulating.start_time = start_time
    simulating.starting_time = t.time()
    simulating.speed = speed


def is_simulating() -> bool:
    return simulating.simulating


def time() -> float:
    if not simulating.simulating:
        return t.time()
    return simulating.start_time + (t.time() - simulating.starting_time) * simulating.speed


def duration(d: float) -> float:
    if not simulating.simulating:
        return d
    du = d / simulating.speed
    return du if du > 2 or d < 2 else 2
