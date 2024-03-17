from typing import Optional

import aioreactive as rx
from aioreactive.create import interval

from .driver import Driver, log
from ..div import time
from ..hal.hal import Hal


class PollingDriver[H: Hal](Driver[H]):
    polling_key: str = 'pollEverySeconds'

    def __init__(self):
        super().__init__()
        self.pollEverySeconds: Optional[float] = None
        self.polling_disposable: Optional[rx.AsyncDisposable] = None

    def _init(self):
        super()._init()
        self.pollEverySeconds = float(self.params[self.polling_key])

    async def start(self) -> None:
        await super().start()
        duration = time.duration(self.pollEverySeconds)
        log.debug(f"doing driver.pollingEvery({self.id}/{self.path}, {duration})")

        async def _poll(n):
            await self.poll()
        self.polling_disposable = await interval(0.5, duration).subscribe_async(_poll)

    async def stop(self) -> None:
        await super().stop()
        if self.polling_disposable:
            await self.polling_disposable.dispose_async()
