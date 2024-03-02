import logging
from copy import deepcopy
from enum import StrEnum, auto
from typing import Optional

import reactivex as rx

from ..div.emit import RawEmit
from ..model import thing as aqt
from ..util.dataclassutil import overwrite_list

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

    def __init__(self, m_driver: aqt.Driver) -> None:
        self.m_driver = m_driver
        self.path: Optional[str] = None
        self.params: Optional[dict[str, str]] = None
        self.status: Status = Status.NO_INIT
        so = rx.subject.BehaviorSubject[RawEmit](self.status)
        self._rx_status_observer: rx.Observer[RawEmit] = so
        self.rx_status_observable: rx.Observable[RawEmit] = so
        self._rx_observers: dict[str, rx.Observer[RawEmit]] = {}
        self.rx_observables: dict[str, rx.Observable[RawEmit]] = {}

    def create_m_device(self, driver_info: Optional[aqt.DriverRef] = None) -> aqt.Device:
        m_device = deepcopy(self.m_driver.templateDevice)
        if driver_info:
            if driver_info.path:
                m_device.driver.path = driver_info.path
            if driver_info.params:
                overwrite_list(m_device.driver.params, driver_info.params)
        return m_device

    def create_m_observable(self) -> aqt.Observable:
        m_observable = self.m_driver.templateDevice.observables[0]
        m_observable.driver = self.m_driver.templateDevice.driver
        return m_observable

    def discover_device_paths(self) -> list[str]:
        return []

    def _status(self, status: Status):
        self.status = status
        self._rx_status_observer.on_next(RawEmit(enumValue=status))

    def _set_subjects(self) -> dict[str, rx.subject.Subject]:
        return {}

    def _init(self):
        pass

    def init(self, path: str, params: dict[str, str]) -> 'Driver':
        log.info(f"doing driver.init({self.id}/{path})")
        self.path = path
        self.params = params
        self._init()
        sos = self._set_subjects()
        self._rx_observers = sos
        self.rx_observables = sos
        self._status(Status.NOT_STARTED)
        return self

    def start(self) -> None:
        log.debug(f"doing driver.start({self.id}/{self.path})")
        self._status(Status.STARTING)

    #   @abstractmethod
    def poll(self) -> None:
        log.debug(f"doing driver.poll({self.id}/{self.path})")
        raise Exception('Not implemented')

    def set(self, rx_key: str, emit: RawEmit) -> None:
        log.debug(f"doing driver.set({self.id}/{self.path}, {rx_key}, {emit})")
        raise Exception('Not implemented')

    def stop(self) -> None:
        log.debug(f"doing driver.stop({self.id}/{self.path})")
        self._status(Status.CLOSING)

    def close(self) -> None:
        log.debug(f"doing driver.close({self.id}/{self.path})")
        for o in self._rx_observers.values():
            o.on_completed()
        self._rx_status_observer.on_completed()
