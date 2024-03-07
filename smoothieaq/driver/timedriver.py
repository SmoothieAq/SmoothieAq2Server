from typing import Optional
from datetime import datetime, timezone
import time as t

import aioreactive as rx

from .driver import Driver, log, Status
from ..div.emit import RawEmit
from ..model import thing as aqt
from ..div import time


class TimeDriver(Driver):
    id = "TimeDriver"
    rx_key: str = 'A'

    def __init__(self, m_driver: aqt.Driver):
        super().__init__(m_driver)
        self.polling_disposable: Optional[rx.AsyncDisposable] = None

    def _set_subjects(self) -> dict[str, rx.AsyncSubject]:
        return {self.rx_key: rx.AsyncSubject[RawEmit]()}

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
        await self._status(Status.RUNNING)

    async def stop(self) -> None:
        await super().stop()
        if self.polling_disposable:
            await self.polling_disposable.dispose_async()
