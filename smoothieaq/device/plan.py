import asyncio
import logging
import random
from asyncio import sleep
from datetime import datetime

import aioreactive as rx
from expression.collections import Block
from expression.system import CancellationTokenSource, CancellationToken

from ..device.device import Device
from ..device.observable import Status, Chore
from ..device.scheduleat import next_schedule_at, time_length
from ..div.emit import RawEmit, ObservableEmit
from ..div.time import time as div_time, duration
from ..model.thing import Schedule, Plan
from ..util.rxutil import await_first

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
    delay = None
    if chore.current_value.enumValue == 'delay':
        delay = chore.current_value.stamp

    plan = chore.m_observable.plan
    interval = (plan.everyDays or 1) * 24 * 60 * 60
    if plan.relativeToLast:
        next = last_run + interval
        if delay and delay + (plan.delayFraction or 0.15) * interval > div_time():
            next = delay + (plan.delayFraction or 0.15) * interval
    else:
        next = round(div_time() / interval, 0) * interval + interval
        close_fraction = plan.skipIfLastCloseFraction or 0.33
        if last_run + close_fraction * interval > next:
            next = next + interval
        elif delay and delay + (plan.delayFraction or 0.15) * interval > div_time():
            next = delay + (plan.delayFraction or 0.15) * interval



    await rx_scheduled.asend(RawEmit(enumValue=Status.SCHEDULE_RUNNING))

    def next_schedule() -> tuple[Schedule, datetime]:
        return (Block.of_seq(device.m_device.schedules)
                .map(lambda s: (s, next_schedule_at(s.at, time_length(s.program.length))))
                .sort_with(lambda s: s[1])
                )[0]

    async def do_schedule(cancellation_token: CancellationToken):
        from .program import do_program
        min_wait = random.random() * 4 + 6
        while True:
            schedule, next = next_schedule()
            # print("!!1", next, schedule)
            log.info(f"On device {device.id}, waiting until {next} for schedule {schedule.id}")
            next_time = next.timestamp()
            while True:
                if cancellation_token.is_cancellation_requested:
                    log.info(f"Schedules cancelled on device {device.id}")
                    return
                wait = next_time - div_time()
                # print("!!2", wait, datetime.fromtimestamp(div_time()))
                if wait > 0.1:
                    await sleep(duration(max(min_wait, wait)))
                else:
                    await rx_scheduled.asend(RawEmit(enumValue=Status.PROGRAM_RUNNING))
                    log.info(f"On device {device.id}, do program on schedule {schedule.id}")
                    await do_program(device, schedule.program, next_time, cancellation_token)
                    await rx_scheduled.asend(RawEmit(enumValue=Status.SCHEDULE_RUNNING))
                    break

    task = asyncio.create_task(do_schedule(cancellation_token_source.token))

    return rx.AsyncDisposable.create(do_dispose)
