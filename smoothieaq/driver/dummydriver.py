import random
from typing import Optional

import reactivex as rx

from smoothieaq.div.emit import RawEmit
from .driver import Status, log
from .pollingdriver import PollingDriver
from ..model import thing as aqt


class DummyDriver(PollingDriver):
    id = "DummyDriver"
    mu_key: str = 'generateGaussMu'
    sigma_key: str = 'generateGaussSigma'
    rx_key: str = 'A'

    def __init__(self, m_driver: aqt.Driver):
        super().__init__(m_driver)
        self.generateGaussMu: Optional[float] = None
        self.generateGaussSigma: Optional[float] = None

    def _set_subjects(self) -> dict[str, rx.subject.Subject]:
        return {self.rx_key: rx.Subject[RawEmit]()}

    def _init(self):
        super()._init()
        self.generateGaussMu = float(self.params[self.mu_key])
        self.generateGaussSigma = float(self.params[self.sigma_key])

    def start(self) -> None:
        super().start()
        self._status(Status.RUNNING)

    def poll(self) -> None:
        log.debug(f"doing driver.poll({self.id}/{self.path})")
        emit = RawEmit(value=random.gauss(self.generateGaussMu, self.generateGaussSigma))
        log.debug(f"doing driver.emit({self.id}/{self.path}, {self.rx_key}, {emit})")
        self._rx_observers[self.rx_key].on_next(emit)
