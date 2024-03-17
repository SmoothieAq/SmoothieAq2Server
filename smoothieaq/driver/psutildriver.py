import logging
import statistics

import psutil
import aioreactive as rx
from expression.collections import Map

from smoothieaq.div.emit import RawEmit
from .driver import Status
from .pollingdriver import PollingDriver
from ..hal.hal import NoHal

log = logging.getLogger(__name__)


class PsutilDriver(PollingDriver[NoHal]):
    id = "PsutilDriver"
    rx_key_percent: str = 'A'
    rx_key_temp: str = 'B'

    def discover_device_paths(self) -> list[str]:
        return ["computer"]

    def _set_subjects(self) -> Map[str, rx.AsyncSubject]:
        return Map.empty().add(
            self.rx_key_percent, rx.AsyncSubject[RawEmit]()
        ).add(
            self.rx_key_temp, rx.AsyncSubject[RawEmit]()
        )

    def _init(self):
        super()._init()

    async def start(self) -> None:
        await super().start()
        await self._status(Status.RUNNING)

    async def poll(self) -> None:

        percent = psutil.cpu_percent()
        if percent:
            emit = RawEmit(value=percent)
            log.debug(f"doing psutil.emit({self.id}/{self.path}, {self.rx_key_percent}, {emit})")
            await self._rx_observers[self.rx_key_percent].asend(emit)

        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            print(temps)
            core = temps['coretemp'] or []
            average_temp = statistics.mean(map(lambda s: s["current"], core))
            if average_temp:
                emit = RawEmit(value=average_temp)
                log.debug(f"doing psutil.emit({self.id}/{self.path}, {self.rx_key_temp}, {emit})")
                await self._rx_observers[self.rx_key_temp].asend(emit)
