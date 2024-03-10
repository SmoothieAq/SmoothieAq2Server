import logging
from enum import StrEnum, auto
from typing import Optional

import aioreactive as rx
from expression.collections import Map

from ..div.emit import RawEmit
from ..util.rxutil import AsyncBehaviorSubject

log = logging.getLogger(__name__)


class Status(StrEnum):
    NO_INIT = auto()
    NOT_STARTED = auto()
    STARTING = auto()
    RUNNING = auto()
    PROGRAM_RUNNING = auto()
    SCHEDULE_RUNNING = auto()
    IN_ERROR = auto()
    CLOSING = auto()


class Driver:
    id: str

    def __init__(self) -> None:
        self.path: Optional[str] = None
        self.params: Optional[Map[str, str]] = None
        self.status: Status = Status.NO_INIT
        so = AsyncBehaviorSubject[RawEmit](self.status)
        self._rx_status_observer: rx.AsyncObserver[RawEmit] = so
        self.rx_status_observable: rx.AsyncObservable[RawEmit] = so
        self._rx_observers: dict[str, rx.AsyncObserver[RawEmit]] = {}
        self.rx_observables: dict[str, rx.AsyncObservable[RawEmit]] = {}

    async def discover_device_paths(self) -> list[str]:
        return []

    async def _status(self, status: Status):
        self.status = status
        await self._rx_status_observer.asend(RawEmit(enumValue=status))

    def _set_subjects(self) -> Map[str, rx.AsyncSubject]:
        return Map.empty()

    def _init(self):
        pass

    def init(self, path: str, params: Map[str, str]) -> 'Driver':
        log.info(f"doing driver.init({self.id}/{path})")
        self.path = path
        self.params = params
        self._init()
        sos = self._set_subjects()
        self._rx_observers = sos
        self.rx_observables = sos
        # self._status(Status.NOT_STARTED)
        return self

    async def start(self) -> None:
        log.debug(f"doing driver.start({self.id}/{self.path})")
        await self._status(Status.STARTING)

    #   @abstractmethod
    async def poll(self) -> None:
        log.debug(f"doing driver.poll({self.id}/{self.path})")
        raise Exception('Not implemented')

    async def set(self, rx_key: str, emit: RawEmit) -> None:
        log.debug(f"doing driver.set({self.id}/{self.path}, {rx_key}, {emit})")
        raise Exception('Not implemented')

    async def stop(self) -> None:
        log.debug(f"doing driver.stop({self.id}/{self.path})")
        await self._status(Status.CLOSING)

    async def close(self) -> None:
        log.debug(f"doing driver.close({self.id}/{self.path})")
        for o in self._rx_observers.values():
            await o.aclose()
        await self._rx_status_observer.aclose()
