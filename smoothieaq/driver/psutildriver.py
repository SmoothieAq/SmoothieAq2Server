import logging
import statistics

import psutil
import reactivex as rx

from smoothieaq.div.emit import RawEmit
from .driver import Status
from .pollingdriver import PollingDriver
from ..model import thing as aqt


log = logging.getLogger(__name__)


class PsutilDriver(PollingDriver):
    id = "PsutilDriver"
    rx_key_percent: str = 'A'
    rx_key_temp: str = 'B'

    def __init__(self, m_driver: aqt.Driver):
        super().__init__(m_driver)

    def discover_device_paths(self) -> list[str]:
        return ["computer"]

    def _set_subjects(self) -> dict[str, rx.subject.Subject]:
        return {self.rx_key_percent: rx.Subject[RawEmit](), self.rx_key_temp: rx.Subject[RawEmit]()}

    def _init(self):
        super()._init()

    def start(self) -> None:
        super().start()
        self._status(Status.RUNNING)

    def poll(self) -> None:

        percent = psutil.cpu_percent()
        if percent:
            emit = RawEmit(value=percent)
            log.debug(f"doing psutil.emit({self.id}/{self.path}, {self.rx_key_percent}, {emit})")
            self._rx_observers[self.rx_key_percent].on_next(emit)

        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            print(temps)
            core = temps['coretemp'] or []
            average_temp = statistics.mean(map(lambda s: s["current"], core))
            if average_temp:
                emit = RawEmit(value=average_temp)
                log.debug(f"doing psutil.emit({self.id}/{self.path}, {self.rx_key_temp}, {emit})")
                self._rx_observers[self.rx_key_temp].on_next(emit)
