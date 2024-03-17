import aioreactive as rx
from expression.collections import Map

from smoothieaq.div.emit import RawEmit
from .driver import Driver, log
from .driver import Status
from ..hal.hal import NoHal


class MemoryDriver(Driver[NoHal]):
    id = "MemoryDriver"
    rx_key: str = 'A'

    def __init__(self):
        super().__init__()

    def _set_subjects(self) -> Map[str, rx.AsyncSubject]:
        return Map.empty().add(self.rx_key, rx.AsyncSubject[RawEmit]())

    async def start(self) -> None:
        await super().start()
        await self._status(Status.RUNNING)

    async def set(self, rx_key: str, emit: RawEmit) -> None:
        log.debug(f"doing driver.set({self.id}/{self.path}, {rx_key}, {emit})")
        # assert rx_key == self.rx_key
        await self._rx_observers[self.rx_key].asend(emit)
