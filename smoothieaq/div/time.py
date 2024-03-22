import time as t
from dataclasses import dataclass
import datetime as dt


@dataclass
class _Simulate:
    simulating: bool = False
    start_time: float = t.time()
    starting_time: float = t.time()
    speed: float = 1
    minDuration: float = 2


simulating = _Simulate()


def simulate(
        start_date: dt.date = dt.date.today(),
        start_time: dt.time = dt.datetime.now().time(),
        speed: float = 1,
        minDuration: float = 2
) -> None:
    simulating.simulating = True
    simulating.start_time = dt.datetime.combine(start_date, start_time).timestamp()
    simulating.starting_time = t.time()
    simulating.speed = speed
    simulating.minDuration = minDuration


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
    return du if du > simulating.minDuration or d < simulating.minDuration else simulating.minDuration
