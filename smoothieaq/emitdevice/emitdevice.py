import asyncio
import logging
from typing import Optional

from reactivex.abc import DisposableBase
from reactivex import operators as op
from reactivex.scheduler.eventloop import AsyncIOScheduler

from ..device.devices import get_rx_device_updates, rx_all_observables
from ..emitdriver.emitdriver import EmitDriver
from ..emitdriver.emitdrivers import find_emit_driver
from ..model import thing as aqt


log = logging.getLogger(__name__)


class EmitDevice:

    def __init__(self) -> None:
        self.m_emit_device: Optional[aqt.EmitDevice] = None
        self.id: Optional[str] = None
        self.driver: Optional[EmitDriver] = None
        self.paused: bool = True
        self.filter: dict[str,bool] = {}
        self._disposables: list[DisposableBase] = []

    def pause(self, paused: bool = True) -> None:
        assert self.m_emit_device.enabled is not False
        self.paused = paused

    def unpause(self) -> None:
        self.pause(False)

    def driver_init(self, driver_ref: aqt.DriverRef, id: str) -> EmitDriver:
        driver = find_emit_driver(driver_ref.id)
        path = driver_ref.path or id
        params = dict(map(lambda p: (p.key, p.value), driver_ref.params or []))
        return driver.init(path, params)

    def update_filter(self, m_device: aqt.Device) -> None:
        def include(id: str, status: bool, t1: tuple[str, str, str], t2: tuple[str, str, str]) -> bool:
            def match(filter: aqt.EmitDeviceFilter) -> bool:
                if filter.id and not filter.id == id:
                    return False
                if filter.statusObservable is not None and not filter.statusObservable == status:
                    return False
                if filter.site is not None and not filter.site == (t2[0] or t1[0]):
                    return False
                if filter.place is not None and not filter.place == (t2[1] or t1[1]):
                    return False
                if filter.category is not None and not filter.category == (t2[2] or t1[2]):
                    return False
                return True

            def any_match(filters: list[aqt.EmitDeviceFilter]) -> bool:
                return not filters or any(map(match, filters))

            return any_match(self.m_emit_device.include) and not any_match(self.m_emit_device.exclude)

        log.debug(f"doing emitdevice.update_filter({m_device.id})")
        t1 = (m_device.site, m_device.place, m_device.category)
        self.filter[m_device.id + '?'] = include(m_device.id + '?', True, t1, t1)
        for m_observable in m_device.observables:
            t2 = (m_observable.site, m_observable.place, m_observable.category)
            id = m_device.id + m_observable.id
            self.filter[id + '?'] = include(id + '?', True, t1, t2)
            self.filter[id] = include(id, False, t1, t2)

    def init(self, m_emit_device: aqt.EmitDevice) -> 'EmitDevice':
        self.m_emit_device = m_emit_device
        self.id = m_emit_device.id
        log.info(f"doing emitdevice.init({self.id})")

        if self.m_emit_device.enabled is not False:
            self.driver = self.driver_init(m_emit_device.driver, self.id)

    def start(self):
        self._disposables.append(get_rx_device_updates().subscribe(on_next=self.update_filter))
        rx = rx_all_observables.pipe(op.filter(lambda e: self.filter.get(e.observable_id, True)))
        if self.m_emit_device.bufferNo or self.m_emit_device.bufferTime:
            rx = rx.pipe(op.buffer_with_time_or_count(self.m_emit_device.bufferTime or 0.5,
                                                      self.m_emit_device.bufferNo or 10))
        else:
            rx = rx.pipe(op.observe_on(AsyncIOScheduler(asyncio.get_event_loop())))
        self._disposables.append(rx.subscribe(on_next=lambda e: self.driver.emit(e)))

    def stop(self):
        for disposable in self._disposables:
            disposable.dispose()
