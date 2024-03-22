import logging
from typing import Optional

import aioreactive as rx

from .observable import Observable, driver_init, Status, Measure, Amount, State, Event
from ..div.emit import ObservableEmit, RawEmit, emit_enum_value, emit_raw_fun
from ..driver.driver import Driver, Status as DriverStatus
from ..model import thing as aqt
from ..util.rxutil import AsyncBehaviorSubject, publish, throwIt

log = logging.getLogger(__name__)


class Device:

    def __init__(self) -> None:
        self.m_device: Optional[aqt.Device] = None
        self.id: Optional[str] = None
        self.status_id: Optional[str] = None
        self.driver: Optional[Driver] = None
        self.rx_status_observable: Optional[rx.AsyncObservable[ObservableEmit]] = None
        self.observables: Optional[dict[str, Observable]] = None
        self.paused: bool = False
        self._rx_paused = AsyncBehaviorSubject[bool](self.paused)
        self._rx_scheduled = AsyncBehaviorSubject[RawEmit](RawEmit(enumValue=Status.RUNNING))
        self._rx_all_subject = rx.AsyncSubject[rx.AsyncObservable[ObservableEmit]]()
        self.rx_all_observables: Optional[rx.AsyncObservable[ObservableEmit]] = None
        self._disposables: list[rx.AsyncDisposable] = []

    async def pause(self, paused: bool = True) -> None:
        log.info(f"doing device.pause({self.id},{paused})")
        assert self.m_device.enabled is not False
        self.paused = paused
        await self._rx_paused.asend(paused)
        for o in self.observables.values():
            await o.pause(paused)
        if paused:
            await self.stop()
        else:
            await self.start()

    async def unpause(self) -> None:
        await self.pause(False)

    def init(self, m_device: aqt.Device) -> 'Device':
        self.m_device = m_device
        self.id = m_device.id
        self.status_id = self.id + '?'

        if self.m_device.enabled is not False:
            s: rx.AsyncObservable[RawEmit]
            if m_device.driver and m_device.driver.id:
                self.driver = driver_init(m_device.driver, self.id)
                s = self.driver.rx_status_observable
            else:
                s = AsyncBehaviorSubject(RawEmit(enumValue=DriverStatus.RUNNING))

            def status(t: tuple[tuple[bool, RawEmit], RawEmit]) -> RawEmit:
                ((paused, scheduled), driver_status) = t
                log.debug(f"evaluating device.status({self.id}, {paused}, {scheduled}, {driver_status}")
                # print("dev stat",self.id, paused,driver_status)
                if paused:
                    return RawEmit(enumValue=Status.PAUSED)
                elif driver_status.enumValue in {DriverStatus.RUNNING, DriverStatus.PROGRAM_RUNNING,
                                                 DriverStatus.SCHEDULE_RUNNING}:
                    return scheduled
                elif driver_status.enumValue in {DriverStatus.IN_ERROR, DriverStatus.CLOSING}:
                    return RawEmit(enumValue=Status.ERROR, note=driver_status.note)
                else:
                    return RawEmit(enumValue=Status.INITIALIZING)

            self.rx_status_observable = rx.pipe(
                self._rx_paused,
                rx.combine_latest(self._rx_scheduled),
                rx.combine_latest(s),
                rx.map(status),
                rx.distinct_until_changed,
                rx.map(emit_raw_fun(self.status_id)),
                publish()
            )
        else:
            self.rx_status_observable = AsyncBehaviorSubject(emit_enum_value(self.status_id, Status.DISABLED))

        def create_observable(mo: aqt.Observable) -> tuple[str, Observable]:
            o: Observable
            if isinstance(mo, aqt.Measure):
                o = Measure()
            elif isinstance(mo, aqt.Amount):
                o = Amount()
            elif isinstance(mo, aqt.State):
                o = State()
            elif isinstance(mo, aqt.Event):
                o = Event()
            else:
                log.error(f"On device {self.id} - Unknown type of Observable {type(mo)}")
                raise Exception(f"Unknown type of Observable {type(mo)}")
            return mo.id, o.init(mo, self)

        self.observables = dict(map(create_observable, m_device.observables or []))

        self.rx_all_observables = rx.pipe(
            rx.from_iterable(([self.rx_status_observable] +
                              [o for ob in self.observables.values() for o in
                               [ob.rx_observable, ob.rx_status_observable]])),
            rx.merge_inner()
        )

        return self

    async def start(self) -> None:
        log.info(f"doing device.start({self.id})")
        assert self.m_device.enabled is not False
        if self.driver:
            await self.driver.start()
        for t, o in [
            ("rx_status", self.rx_status_observable),
        ]:
            self._disposables.append(await o.subscribe_async(throw=throwIt(t)))
            self._disposables.append(await o.connect())
        for o in self.observables.values():
            await o.start()

        if self.m_device.schedules:
            from .schedules import schedules
            self._disposables.append(await schedules(self.m_device.schedules, self, self._rx_scheduled))

    async def stop(self) -> None:
        log.info(f"doing device.stop({self.id})")
        for o in self.observables.values():
            await o.stop()
        if self.driver:
            await self.driver.stop()
        for d in self._disposables:
            await d.dispose_async()
        self._disposables = []

    async def poll(self) -> None:
        assert self.m_device.enabled is not False
        await self.driver.poll()

    async def close(self) -> None:
        log.info(f"doing device.close({self.id})")
        for o in self.observables.values():
            await o.close()
        await self._rx_paused.aclose()
        await self._rx_scheduled.aclose()
