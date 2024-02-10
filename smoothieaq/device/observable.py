import time
from enum import StrEnum, auto

import reactivex as rx
import reactivex.operators as op
from reactivex.disposable import Disposable

from ..driver.drivers import *
from ..driver.driver import Status as DriverStatus
from ..emit import *
from .expression import as_observable


class Status(StrEnum):
    RUNNING = auto()
    PAUSED = auto()
    WARNING = auto()
    ALARM = auto()
    ERROR = auto()
    INITIALIZING = auto()
    DISABLED = auto()


def driver_init(driver_ref: aqt.DriverRef) -> Optional[Driver]:
    if not driver_ref or not driver_ref.id:
        return None
    driver = find_driver(driver_ref.id)
    path = driver_ref.path or ""
    params = dict(map(lambda p: (p.key, p.value), driver_ref.params or []))
    return driver.init(path, params)


class Observable:

    def __init__(self) -> None:
        self.m_observable: Optional[aqt.Observable] = None
        self.device: Optional['Device'] = None
        self.id: Optional[str] = None
        self.status_id: Optional[str] = None
        self.driver: Optional[Driver] = None
        self.rx_status_observable: Optional[rx.Observable[ObservableEmit]] = None
        self.rx_observable: Optional[rx.Observable[ObservableEmit]] = None
        self.paused: bool = False
        self._rx_paused = rx.subject.BehaviorSubject[bool](self.paused)

    def pause(self, paused: bool = True) -> None:
        self.paused = paused
        self._rx_paused.on_next(paused)
        if paused:
            self.stop()
        else:
            self.start()

    def unpause(self) -> None:
        self.pause(False)

    def enabled(self) -> bool:
        return self.m_observable.enabled is not False and self.device.m_device.enabled is not False

    def init(self, m_observable: aqt.Observable, device: 'Device') -> 'Observable':
        self.m_observable = m_observable
        self.device = device
        self.id = device.id + ':' + m_observable.id
        self.status_id = self.id + '?'

        if self.enabled():
            self.init_enabled()
        else:
            self.rx_status_observable = rx.of(emit_enum_value(self.status_id, Status.DISABLED))

        return self

    def init_enabled(self):
        o: rx.Observable[RawEmit]
        s: rx.Observable[RawEmit]
        if self.m_observable.driver and self.m_observable.driver.id:
            self.driver = driver_init(self.m_observable.driver)
            o = self.driver.rx_observables['A']
            s = self.driver.rx_status_observable
        else:
            o = self.device.driver.rx_observables[self.m_observable.id]
            s = self.device.driver.rx_status_observable
        self.rx_observable = o.pipe(
            op.map(emit_raw_fun(self.id))
        )

        def status(t: tuple[ObservableEmit, bool, RawEmit]) -> ObservableEmit:
            (device_status, paused, driver_status) = t
            # print("obs stat",self.id, device_status, paused, driver_status)
            if not device_status.enumValue == Status.RUNNING:
                return emit_enum_value(self.status_id, device_status.enumValue)
            if paused:
                return emit_enum_value(self.status_id, Status.PAUSED)
            elif driver_status.enumValue in {DriverStatus.RUNNING, DriverStatus.PROGRAM_RUNNING,
                                             DriverStatus.SCHEDULE_RUNNING}:
                return emit_enum_value(self.status_id, Status.RUNNING)
            elif driver_status.enumValue in {DriverStatus.IN_ERROR, DriverStatus.CLOSING}:
                return emit_enum_value(self.status_id, Status.ERROR)
            else:
                return emit_enum_value(self.status_id, Status.INITIALIZING)

        self.rx_status_observable = rx.combine_latest(self.device.rx_status_observable, self._rx_paused, s).pipe(
            op.map(status),
            op.distinct_until_changed(lambda e: e.enumValue)
        )

    def start(self) -> None:
        assert self.enabled()
        if self.driver:
            self.driver.start()

    def stop(self) -> None:
        if self.driver:
            self.driver.stop()

    def close(self) -> None:
        self._rx_paused.on_completed()

    def _driver(self) -> Driver:
        return self.driver or self.device.driver


class Measure(Observable):


    def measurement(self, value: float, note: str = None) -> None:
        self._driver().set(self.m_observable.id, RawEmit(value=value, note=note))


class _SetObservable(Observable):

    def __init__(self):
        super().__init__()
        self.set_expr_disposable: Optional[Disposable] = None

    def set_value(self, value: float | str | RawEmit, note: str = None):
        e: RawEmit
        if isinstance(value, float):
            e = RawEmit(value=value, note=note)
        elif isinstance(value, str):
            e = RawEmit(enumValue=value, note=note)
        elif isinstance(value, RawEmit):
            e = value
        else:
            e = RawEmit()
        self._driver().set(self.m_observable.id, e)

    def start(self) -> None:
        super().start()
        if self.m_observable.setExpr:
            self.set_expr_disposable = as_observable(self.m_observable.setExpr, self.device.id).subscribe(
                on_next=lambda e: self.set_value(e)
            )

    def stop(self) -> None:
        super().stop()
        if self.set_expr_disposable:
            self.set_expr_disposable.dispose()


class Amount(_SetObservable):
    pass


class State(_SetObservable):
    pass


class Event(Observable):
    pass
