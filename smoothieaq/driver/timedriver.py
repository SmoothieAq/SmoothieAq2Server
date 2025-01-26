import time as t
from typing import Optional

import aioreactive as rx
from expression.collections import Map

from .driver import Driver, Status
from ..div import time
from ..div.emit import RawEmit
from ..hal.hal import NoHal


class TimeDriver(Driver[NoHal]):
    id = "TimeDriver"
    rx_key: str = 'A'

    def __init__(self):
        super().__init__()
        self.polling_disposable: Optional[rx.AsyncDisposable] = None

    def _set_subjects(self) -> Map[str, rx.AsyncSubject]:
        return Map.empty().add(self.rx_key, rx.AsyncSubject[RawEmit]())

    async def start(self) -> None:
        await super().start()
        duration = time.duration(60.)
        first = int(t.time() / duration) * duration + duration

        def tick(at):
            async def _tick(n):
                await self._rx_observers[self.rx_key].asend(RawEmit(value=time.time(), enumValue="tick"))
                next = at + duration
                await self.polling_disposable.dispose_async()
                self.polling_disposable = await rx.timer(next - t.time()).subscribe_async(tick(next))

            return _tick

        self.polling_disposable = await rx.timer(first - t.time()).subscribe_async(tick(first))
        await self.set_status(Status.RUNNING)

    async def stop(self) -> None:
        await super().stop()
        if self.polling_disposable:
            await self.polling_disposable.dispose_async()
