import aioreactive as rx

from smoothieaq.div.emit import RawEmit
from .driver import Driver, log
from .driver import Status
from ..model import thing as aqt


class MemoryDriver(Driver):
    id = "MemoryDriver"
    rx_key: str = 'A'

    def __init__(self, m_driver: aqt.Driver):
        super().__init__(m_driver)

    def _set_subjects(self) -> dict[str, rx.AsyncSubject]:
        return {self.rx_key: rx.AsyncSubject[RawEmit]()}

    async def start(self) -> None:
        await super().start()
        await self._status(Status.RUNNING)

    async def set(self, rx_key: str, emit: RawEmit) -> None:
        log.debug(f"doing driver.set({self.id}/{self.path}, {rx_key}, {emit})")
        assert rx_key == self.rx_key
        await self._rx_observers[rx_key].asend(emit)
