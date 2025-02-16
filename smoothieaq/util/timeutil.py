from datetime import time, timedelta, datetime
from typing import Optional

from expression.collections import Seq, Block

from smoothieaq.div.time import duration, time as divtime
from smoothieaq.util.rxutil import ix


def time_at_day(timeStr: str) -> time: # mm:ss
    hour, minute = timeStr.split(":")
    return time(hour=int(hour), minute=int(minute))


def time_length(lengthStr: str) -> timedelta: # [[hh:]mm:]ss
    elms = lengthStr.split(":")
    if len(elms) == 3:
        return timedelta(hours=int(elms[0]), minutes=int(elms[1]), seconds=float(elms[2]))
    if len(elms) == 2:
        return timedelta(minutes=int(elms[0]), seconds=float(elms[1]))
    return timedelta(seconds=float(elms[0]))


def weekday(weekdayStr: str) -> int:
    return ["mo", "tu", "we", "th", "fr", "sa", "su"].index(weekdayStr)


def weekdays(weekdayStrs: Optional[list[str]]) -> Seq[int]:
    if weekdayStrs is None:
        return ix(range(0, 7))
    return ix(Block.of_seq(weekdayStrs).map(weekday).sort())


def waiting_time(at: datetime) -> float:
    return duration((at - datetime.fromtimestamp(divtime())).total_seconds())
