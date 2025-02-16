import asyncio
import logging
from asyncio import sleep
from datetime import datetime

import aioreactive as rx
from expression.collections import Block
from expression.collections.seq import concat
from expression.system import CancellationTokenSource

from ..device.observable import Status, Chore
from ..div.time import time as div_time, duration
from ..util.timeutil import weekdays, time_at_day

log = logging.getLogger(__name__)


async def plan(chore: Chore) -> rx.AsyncDisposable:
    cancellation_token_source = CancellationTokenSource()

    async def do_dispose():
        cancellation_token_source.cancel()
        await chore.rx_status_asend(Status.IDLE)

    try:
        last_run = float(chore.current_value.note)
    except ValueError:
        last_run = 0
    except TypeError:
        last_run = 0
    delay = None
    if chore.current_value.enumValue == 'delay':
        delay = chore.current_value.stamp

    day = 24 * 60 * 60
    oneTime = chore.m_observable.oneTime
    if oneTime or not chore.m_observable.plan:
        if oneTime and oneTime.atDate:
            next = datetime.strptime(oneTime.atDate,'%y-%m-%d').timestamp()
            if oneTime.atTime:
                warning = next
                next += time_at_day(oneTime.atTime)
                alarm = next
            else:
                warning = next
                alarm = next + day
        else:
            next = div_time()
            warning = next
            alarm = next
    else:
        plan = chore.m_observable.plan
        interval = (plan.everyDays or 1) * day
        if plan.relativeToLast:
            next = last_run + interval
            if delay and delay + (plan.delayFraction or 0.15) * interval > div_time():
                next = delay + (plan.delayFraction or 0.15) * interval
        else:
            next = round(div_time() / interval, 0) * interval #+ interval
            close_fraction = plan.skipIfLastCloseFraction or 0.33
            if last_run + close_fraction * interval > next:
                next = next + interval
            elif delay and delay + (plan.delayFraction or 0.15) * interval > div_time():
                next = delay + (plan.delayFraction or 0.15) * interval

        next_datetime = datetime.fromtimestamp(next)
        delta_days = (Block.of_seq(concat(weekdays(plan.atWeekDays).map(lambda n: n - 7), weekdays(plan.atWeekDays), weekdays(plan.atWeekDays).map(lambda n: n + 7)))
                      .map(lambda n: n - next_datetime.weekday())
                      .sort_with(lambda n: abs(n)-n/10)[0])
        next += delta_days * day
        next += time_at_day(plan.atTime)
        warning = next
        alarm = next + day

    async def do_plan():
        if cancellation_token_source.is_cancellation_requested: return
        t = div_time()
        if t < warning:
            await sleep(duration(warning - t))
            if cancellation_token_source.is_cancellation_requested: return
            await chore.rx_status_asend(Status.WARNING, f"Soon {next}")
        t = div_time()
        if t < alarm:
            await sleep(duration(alarm - t))
            if cancellation_token_source.is_cancellation_requested: return
        await chore.rx_status_asend(Status.ALARM, f"Overdue {next}")

    task = asyncio.create_task(do_plan())

    return rx.AsyncDisposable.create(do_dispose)

