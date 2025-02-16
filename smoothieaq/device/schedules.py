import asyncio
import logging
import random
from asyncio import sleep
from datetime import datetime

import aioreactive as rx
from expression.collections import Block
from expression.system import CancellationTokenSource, CancellationToken

from ..device.device import Device
from ..device.observable import Status
from ..device.scheduleat import next_schedule_at
from ..util.timeutil import time_length
from ..div.emit import RawEmit
from ..div.time import time as div_time, duration
from ..model.thing import Schedule

log = logging.getLogger(__name__)


async def schedules(schedules: list[Schedule], device: Device, rx_scheduled: rx.AsyncObserver) -> rx.AsyncDisposable:
    cancellation_token_source = CancellationTokenSource()

    async def do_dispose():
        cancellation_token_source.cancel()
        await rx_scheduled.asend(RawEmit(enumValue=Status.RUNNING))

    await rx_scheduled.asend(RawEmit(enumValue=Status.SCHEDULE_RUNNING))

    def next_schedule() -> tuple[Schedule, datetime]:
        return (Block.of_seq(device.m_device.schedules)
                .map(lambda s: (s, next_schedule_at(s.atTime, time_length(s.program.length))))
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
