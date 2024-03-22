import logging
from datetime import timedelta, time, datetime
from typing import Optional

from expression.collections import Seq, Block
from expression.collections.seq import concat

from ..div.time import time as divtime, duration
from ..model.thing import ScheduleAt, AtWeekday
from ..util.rxutil import ix

log = logging.getLogger(__name__)


def waiting_time(at: datetime) -> float:
    return duration((at - datetime.fromtimestamp(divtime())).total_seconds())


def next_schedule_at(at: ScheduleAt, length: timedelta) -> datetime:
    """
    Find next start time, which is the first one that finishes in the future
    :param at: the schedule definition
    :param length: length of the schedule
    :return: the time to start, may be in the past, but after length you will be in the future
    """
    match at:
        case AtWeekday():
            return next_at_weekday(at, length)
        case _:
            log.error(f"Unknown ScheduleAt type {at}")
            return datetime.now()


def next_at_weekday(at: AtWeekday, length: timedelta) -> datetime:
    now = datetime.fromtimestamp(divtime() + 2)
    delta_days = (ix(concat(weekdays(at.every), weekdays(at.every).map(lambda n: n + 7)))
                  .map(lambda n: n - now.weekday())
                  .filter(lambda n: n >= -1))
    at_day = time_at_day(at.at)
    delta_time = (datetime.combine(now.date(), at_day) - now) + length
    delta_day = (delta_days
                 .map(lambda dd: (dd, now + timedelta(days=dd) + delta_time))
                 .filter(lambda d: d[1] > now).to_list()[0][0])
    # print(">2>",now,delta_days,at_day,delta_time,delta_day,datetime.combine((now - timedelta(days=delta_day)).date(), at_day))
    return datetime.combine((now - timedelta(days=delta_day)).date(), at_day)


def time_at_day(timeStr: str) -> time:
    hour, minute = timeStr.split(":")
    return time(hour=int(hour), minute=int(minute))


def time_length(lengthStr: str) -> timedelta:
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
