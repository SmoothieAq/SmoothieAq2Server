import logging
from datetime import timedelta, datetime

from expression.collections.seq import concat

from ..div.time import time as divtime
from ..model.thing import ScheduleAt, AtWeekday
from ..util.rxutil import ix
from ..util.timeutil import time_at_day, weekdays

log = logging.getLogger(__name__)


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


