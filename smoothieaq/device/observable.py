import time
from enum import StrEnum, auto
from typing import Optional

import reactivex as rx
import reactivex.operators as op

import smoothieaq.model.thing as aqt
from smoothieaq.driver.drivers import *
from smoothieaq.driver.driver import Status as DriverStatus
from smoothieaq.emit import *


class Status(StrEnum):
    RUNNING = auto()
    PAUSED = auto()
    WARNING = auto()
    ALARM = auto()
    ERROR = auto()
    INITIALIZING = auto()
    DISABLED = auto()


def _find_driver(driver_ref: aqt.DriverRef) -> Optional[Driver]:
    if not driver_ref or not driver_ref.id:
        return None
    driver = find_driver(driver_ref.id)
    path = driver_ref.path or ""
    params = dict(map(lambda p: (p.key, p.value), driver_ref.params))
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
            o: rx.Observable[RawEmit]
            s: rx.Observable[RawEmit]
            if m_observable.driver and m_observable.driver.id:
                self.driver = _find_driver(m_observable.driver)
                o = self.driver.rx_observables['A']
                s = self.driver.rx_status_observable
            else:
                o = device.driver.rx_observables[m_observable.id]
                s = device.driver.rx_status_observable
            self.rx_observable = o.pipe(
                op.map(lambda e: emit_raw(self.id, e))
            )

            def status(t: tuple[ObservableEmit, bool, RawEmit]) -> ObservableEmit:
                (device_status, paused, driver_status) = t
                #print("obs stat",self.id, device_status, paused, driver_status)
                if not device_status.enumValue == Status.RUNNING:
                    return emit_enum_value(self.status_id, device_status.enumValue)
                if paused:
                    return emit_enum_value(self.status_id, Status.PAUSED)
                elif driver_status.enumValue in {DriverStatus.RUNNING, DriverStatus.PROGRAM_RUNNING, DriverStatus.SCHEDULE_RUNNING}:
                    return emit_enum_value(self.status_id, Status.RUNNING)
                elif driver_status.enumValue in {DriverStatus.IN_ERROR, DriverStatus.CLOSING}:
                    return emit_enum_value(self.status_id, Status.ERROR)
                else:
                    return emit_enum_value(self.status_id, Status.INITIALIZING)

            self.rx_status_observable = rx.combine_latest(self.device.rx_status_observable, self._rx_paused, s).pipe(
                op.map(status),
                op.distinct_until_changed(lambda e: e.enumValue)
            )
        else:
            self.rx_status_observable = rx.of(emit_enum_value(self.status_id, Status.DISABLED))

        return self

    def start(self) -> None:
        assert self.enabled()
        if self.driver:
            self.driver.start()

    def stop(self) -> None:
        if self.driver:
            self.driver.stop()

    def close(self) -> None:
        self._rx_paused.on_completed()


class Device:

    def __init__(self) -> None:
        self.m_device: Optional[aqt.Device] = None
        self.id: Optional[str] = None
        self.status_id: Optional[str] = None
        self.driver: Optional[Driver] = None
        self.rx_status_observable: Optional[rx.Observable[ObservableEmit]] = None
        self.observables: Optional[dict[str, Observable]] = None
        self.paused: bool = False
        self._rx_paused = rx.subject.BehaviorSubject[bool](self.paused)
        self._rx_all_subject = rx.Subject[rx.Observable[ObservableEmit]]()
        self.rx_all_observables: Optional[rx.Observable[ObservableEmit]] = None

    def pause(self, paused: bool = True) -> None:
        self.paused = paused
        self._rx_paused.on_next(paused)
        for o in self.observables.values():
            o.pause(paused)
        if paused:
            self.stop()
        else:
            self.start()

    def unpause(self) -> None:
        self.pause(False)

    def init(self, m_device: aqt.Device) -> 'Device':
        self.m_device: aqt.Device = m_device
        self.id: str = m_device.id
        self.status_id = self.id + '?'

        if self.m_device.enabled is not False:
            s: rx.Observable[RawEmit]
            if m_device.driver and m_device.driver.id:
                self.driver = _find_driver(m_device.driver)
                s = self.driver.rx_status_observable
            else:
                s = rx.of(RawEmit(enumValue=DriverStatus.RUNNING))

            def status(t: tuple[bool, RawEmit]) -> ObservableEmit:
                (paused, driver_status) = t
                #print("dev stat",self.id, paused,driver_status)
                if paused:
                    return emit_enum_value(self.status_id, Status.PAUSED)
                elif driver_status.enumValue in {DriverStatus.RUNNING, DriverStatus.PROGRAM_RUNNING, DriverStatus.SCHEDULE_RUNNING}:
                    return emit_enum_value(self.status_id, Status.RUNNING)
                elif driver_status.enumValue in {DriverStatus.IN_ERROR, DriverStatus.CLOSING}:
                    return emit_enum_value(self.status_id, Status.ERROR)
                else:
                    return emit_enum_value(self.status_id, Status.INITIALIZING)

            self.rx_status_observable = rx.combine_latest(self._rx_paused, s).pipe(
                op.map(status),
                op.distinct_until_changed(lambda e: e.enumValue)
            )
        else:
            self.rx_status_observable = rx.of(emit_enum_value(self.status_id, Status.DISABLED))

        self.observables = dict(map(lambda o: (o.id, Observable().init(o, self)), m_device.observables or []))

        self.rx_all_observables = rx.from_list(([self.rx_status_observable] +
                                                [o for ob in self.observables.values() for o in
                                                 [ob.rx_observable, ob.rx_status_observable]])).pipe(
            op.merge_all()
        )

        return self

    def start(self) -> None:
        assert self.m_device.enabled is not False
        if self.driver:
            self.driver.start()
        for o in self.observables.values():
            o.start()

    def stop(self) -> None:
        for o in self.observables.values():
            o.stop()
        if self.driver:
            self.driver.stop()

    def close(self) -> None:
        for o in self.observables.values():
            o.close()
        self._rx_paused.on_completed()
