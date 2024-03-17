import random
from typing import Optional

import aioreactive as rx
from expression.collections import Map

from smoothieaq.div.emit import RawEmit
from .driver import Status, log
from .pollingdriver import PollingDriver
from ..hal.hal import NoHal


class DummyDriver(PollingDriver[NoHal]):
    id = "DummyDriver"
    mu_key: str = 'generateGaussMu'
    sigma_key: str = 'generateGaussSigma'
    rx_key: str = 'A'

    def __init__(self):
        super().__init__()
        self.generateGaussMu: Optional[float] = None
        self.generateGaussSigma: Optional[float] = None

    def _set_subjects(self) -> Map[str, rx.AsyncSubject]:
        return Map.empty().add(self.rx_key, rx.AsyncSubject[RawEmit]())

    def _init(self):
        super()._init()
        self.generateGaussMu = float(self.params[self.mu_key])
        self.generateGaussSigma = float(self.params[self.sigma_key])

    async def start(self) -> None:
        await super().start()
        await self._status(Status.RUNNING)

    async def poll(self) -> None:
        log.debug(f"doing driver.poll({self.id}/{self.path})")
        emit = RawEmit(value=random.gauss(self.generateGaussMu, self.generateGaussSigma))
        log.debug(f"doing driver.emit({self.id}/{self.path}, {self.rx_key}, {emit})")
        await self._rx_observers[self.rx_key].asend(emit)
