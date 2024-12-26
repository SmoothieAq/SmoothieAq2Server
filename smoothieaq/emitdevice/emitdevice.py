import asyncio
import logging
from typing import Optional

import aioreactive as rx

from ..device.devices import get_rx_device_updates, rx_all_observables
from ..emitdriver.emitdriver import EmitDriver
from ..emitdriver.emitdrivers import find_emit_driver
from ..model import thing as aqt
from ..util.rxutil import buffer_with_time, trace

log = logging.getLogger(__name__)


class EmitDevice:

    def __init__(self) -> None:
        self.m_emit_device: Optional[aqt.EmitDevice] = None
        self.id: Optional[str] = None
        self.driver: Optional[EmitDriver] = None
        self.paused: bool = True
        self.filter: dict[str, bool] = {}
        self._disposables: list[rx.AsyncDisposable] = []

    async def pause(self, paused: bool = True) -> None:
        assert self.m_emit_device.enabled is not False
        self.paused = paused

    async def unpause(self) -> None:
        await self.pause(False)

    async def driver_init(self, driver_ref: aqt.DriverRef, id: str) -> EmitDriver:
        driver = find_emit_driver(driver_ref.id)
        path = driver_ref.path or id
        params = dict(map(lambda p: (p.key, p.value), driver_ref.params or []))
        return await driver.init(path, params)

    async def update_filter(self, m_device: aqt.Device) -> None:
        def include(id: str, status: bool, t1: tuple[str, str, str, str], t2: tuple[str, str, str, str]) -> bool:
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
                if filter.type is not None and not filter.type == (t2[3] or t1[3]):
                    return False
                return True

            def any_match(filters: list[aqt.EmitDeviceFilter]) -> bool:
                return not filters or any(map(match, filters))

            return any_match(self.m_emit_device.include) and not any_match(self.m_emit_device.exclude)

        log.debug(f"doing emitdevice.update_filter({m_device.id})")
        t1 = (m_device.site, m_device.place, m_device.category, m_device.type)
        self.filter[m_device.id + '?'] = include(m_device.id + '?', True, t1, t1)
        for m_observable in m_device.observables:
            t2 = (m_observable.site, m_observable.place, m_observable.category, m_observable.type)
            id = m_device.id + m_observable.id
            self.filter[id + '?'] = include(id + '?', True, t1, t2)
            self.filter[id] = include(id, False, t1, t2)

    async def init(self, m_emit_device: aqt.EmitDevice):
        self.m_emit_device = m_emit_device
        self.id = m_emit_device.id
        log.info(f"doing emitdevice.init({self.id})")

        if self.m_emit_device.enabled is not False:
            self.driver = await self.driver_init(m_emit_device.driver, self.id)

    async def start(self):
        log.info(f"doing emitdevice.start({self.id})")
        self._disposables.append(await rx.pipe(get_rx_device_updates(), trace()).subscribe_async(self.update_filter))
        o = rx.pipe(
            rx_all_observables,
            rx.filter(lambda e: self.filter.get(e.observable_id, True)),
            buffer_with_time(self.m_emit_device.bufferTime or 0.5, self.m_emit_device.bufferNo or 10)
        )
        self._disposables.append(await o.subscribe_async(self.driver.emit))

    async def stop(self):
        log.info(f"doing emitdevice.stop({self.id})")
        for disposable in self._disposables:
            await disposable.dispose_async()
