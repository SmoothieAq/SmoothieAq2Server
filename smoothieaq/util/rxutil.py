import asyncio
from typing import Generator

import reactivex as rx
from reactivex import operators as op
from reactivex.notification import OnNext, OnError
from reactivex.scheduler.eventloop import AsyncIOScheduler


# Largely from https://blog.oakbits.com/rxpy-and-asyncio.html
async def generator[T](obs: rx.Observable[T], loop=asyncio.get_event_loop()) -> Generator[T, None, None]:
    queue = asyncio.Queue[rx.Notification[T]]()

    def on_next(i):
        queue.put_nowait(i)

    disposable = obs.pipe(op.materialize()).subscribe(
        on_next=on_next,
        scheduler=AsyncIOScheduler(loop=loop)
    )

    try:
        while True:
            i = await queue.get()
            if isinstance(i, OnNext):
                yield i.value
                queue.task_done()
            elif isinstance(i, OnError):
                raise Exception(i.value)
            else:
                break
    finally:
        if disposable:
            disposable.dispose()
