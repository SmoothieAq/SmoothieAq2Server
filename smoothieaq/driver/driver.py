from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Optional

import reactivex as rx

from smoothieaq.emit import RawEmit
from ..model import thing as aqt


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

    def create_m_device(self) -> aqt.Device:
        return self.m_driver.templateDevice

    def create_m_observable(self) -> aqt.Observable:
        m_observable = self.m_driver.templateDevice.observables[0]
        m_observable.driver = self.m_driver.templateDevice.driver
        return m_observable

    def find_device_paths(self) -> list[str]:
        return []

    def _status(self, status: Status):
        self.status = status
        self._rx_status_observer.on_next(RawEmit(enumValue=status))

    def _set_subjects(self) -> dict[str, rx.subject.Subject]:
        return {}

    def _init(self):
        pass

    def init(self, path: str, params: dict[str, str]) -> 'Driver':
        self.path = path
        self.params = params
        sos = self._set_subjects()
        self._rx_observers = sos
        self.rx_observables = sos
        self._init()
        self._status(Status.NOT_STARTED)
        return self

    def start(self) -> None:
        self._status(Status.STARTING)

    #   @abstractmethod
    def poll(self) -> None:
        raise Exception('Not implemented')

    def set(self, rx_key: str, emit: RawEmit) -> None:
        raise Exception('Not implemented')

    def stop(self) -> None:
        self._status(Status.CLOSING)

    def close(self) -> None:
        for o in self._rx_observers.values():
            o.on_completed()
        self._rx_status_observer.on_completed()
