from typing import Optional

import aioreactive as rx

from .observable import Observable, driver_init, Status, Measure, Amount, State, Event
from ..div.emit import ObservableEmit, RawEmit, emit_enum_value, emit_raw_fun
from ..driver.driver import Driver, Status as DriverStatus
from ..model import thing as aqt
from ..util.rxutil import AsyncBehaviorSubject


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
        self._rx_all_subject = rx.AsyncSubject[rx.AsyncObservable[ObservableEmit]]()
        self.rx_all_observables: Optional[rx.AsyncObservable[ObservableEmit]] = None

    async def pause(self, paused: bool = True) -> None:
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

            def status(t: tuple[bool, RawEmit]) -> RawEmit:
                (paused, driver_status) = t
                # print("dev stat",self.id, paused,driver_status)
                if paused:
                    return RawEmit(enumValue=Status.PAUSED)
                elif driver_status.enumValue in {DriverStatus.RUNNING, DriverStatus.PROGRAM_RUNNING,
                                                 DriverStatus.SCHEDULE_RUNNING}:
                    return RawEmit(enumValue=Status.RUNNING)
                elif driver_status.enumValue in {DriverStatus.IN_ERROR, DriverStatus.CLOSING}:
                    return RawEmit(enumValue=Status.ERROR, note=driver_status.note)
                else:
                    return RawEmit(enumValue=Status.INITIALIZING)

            self.rx_status_observable = rx.pipe(
                self._rx_paused,
                rx.combine_latest(s),
                rx.map(status),
                rx.distinct_until_changed,
                rx.map(emit_raw_fun(self.status_id))
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
        assert self.m_device.enabled is not False
        if self.driver:
            await self.driver.start()
        for o in self.observables.values():
            await o.start()

    async def stop(self) -> None:
        for o in self.observables.values():
            await o.stop()
        if self.driver:
            await self.driver.stop()

    async def poll(self) -> None:
        assert self.m_device.enabled is not False
        self.driver.poll()

    async def close(self) -> None:
        for o in self.observables.values():
            await o.close()
        await self._rx_paused.aclose()
