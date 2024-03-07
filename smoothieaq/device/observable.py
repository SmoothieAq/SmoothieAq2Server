import logging
from enum import StrEnum, auto
from typing import Optional, Callable

import aioreactive as rx

from .expression import as_observable
from ..div.emit import RawEmit, ObservableEmit, emit_enum_value, emit_raw_fun
from ..driver.driver import Status as DriverStatus, Driver
from ..driver.drivers import find_driver
from ..model import thing as aqt
from ..util.rxutil import ix, AsyncBehaviorSubject, publish, distinct_until_changed, take_first_async

log = logging.getLogger(__name__)


class Status(StrEnum):
    RUNNING = auto()
    PAUSED = auto()
    WARNING = auto()
    ALARM = auto()
    ERROR = auto()
    INITIALIZING = auto()
    DISABLED = auto()


def driver_init(driver_ref: aqt.DriverRef, id: str) -> Optional[Driver]:
    if not driver_ref or not driver_ref.id:
        return None
    driver = find_driver(driver_ref.id)
    path = driver_ref.path or id
    params = dict(ix(driver_ref.params or []).map(lambda p: (p.key, p.value)))
    return driver.init(path, params)


def _rx_require(
        rx1: Optional[rx.AsyncObservable[RawEmit]], rx2: Optional[rx.AsyncObservable[RawEmit]]
) -> Optional[rx.AsyncObservable[RawEmit]]:
    def alarm(e1: RawEmit, e2: RawEmit) -> RawEmit:
        if e1.enumValue == Status.ALARM:
            return e1
        if e2.enumValue == Status.ALARM:
            return e2
        if e1.enumValue == Status.WARNING:
            return e1
        return e2

    if not rx1:
        return rx2
    if not rx2:
        return rx1
    return rx.pipe(
        rx1,
        rx.combine_latest(rx2),
        rx.starmap(alarm)
    )


class Observable[MO: aqt.AbstractObservable]:

    def __init__(self) -> None:
        from .device import Device
        self.m_observable: Optional[MO] = None
        self.device: Optional['Device'] = None
        self.id: Optional[str] = None
        self.status_id: Optional[str] = None
        self.driver: Optional[Driver] = None
        self.rx_status_observable: Optional[rx.AsyncObservable[ObservableEmit]] = None
        self.rx_observable: Optional[rx.AsyncObservable[ObservableEmit]] = None
        self.paused: bool = False
        self._rx_paused = AsyncBehaviorSubject(self.paused)
        self._rx_require: rx.AsyncObservable[RawEmit] = AsyncBehaviorSubject(RawEmit(enumValue=Status.RUNNING))
        self._disposables: list[rx.AsyncDisposable] = []

    async def pause(self, paused: bool = True) -> None:
        assert self.enabled()
        log.info(f"doing observable.pause({self.id},{paused})")
        self.paused = paused
        await self._rx_paused.asend(paused)
        if paused:
            await self.stop()
        else:
            await self.start()

    async def unpause(self) -> None:
        await self.pause(False)

    def enabled(self) -> bool:
        return self.m_observable.enabled is not False and self.device.m_device.enabled is not False

    def init(self, m_observable: aqt.Observable, device: 'Device') -> 'Observable':
        self.id = device.id + ':' + m_observable.id
        log.info(f"doing observable.init({self.id},{m_observable.name})")
        self.m_observable = m_observable
        self.device = device
        self.status_id = self.id + '?'

        if self.enabled():
            self.init_enabled()
        else:
            self.rx_status_observable = AsyncBehaviorSubject(emit_enum_value(self.status_id, Status.DISABLED))

        return self

    def _rx_prefilter(self, o: rx.AsyncObservable[RawEmit]) -> rx.AsyncObservable[RawEmit]:
        return o

    def init_enabled(self):
        from .devices import get_last_emit

        o: rx.AsyncObservable[RawEmit]
        s: rx.AsyncObservable[RawEmit]
        if self.m_observable.driver and self.m_observable.driver.id:
            log.debug(f"observing own driver({self.driver.id}) on observable({self.id})")
            self.driver = driver_init(self.m_observable.driver, self.id)
            o = self.driver.rx_observables['A']
            s = self.driver.rx_status_observable
        elif self.device.driver:
            log.info(f"observing device driver({self.device.driver.id}) on observable({self.id})")
            o = self.device.driver.rx_observables[self.m_observable.id]
            s = self.device.driver.rx_status_observable
        elif self.m_observable.expr:
            log.debug(f"observing expression on observable({self.id})")
            o = as_observable(self.m_observable.expr, self.device.id)
            s = AsyncBehaviorSubject(RawEmit(enumValue=DriverStatus.RUNNING))
        else:
            log.error(f"nothing to observe on observable({self.id})")
            o = AsyncBehaviorSubject(RawEmit())
            s = AsyncBehaviorSubject(RawEmit(enumValue=DriverStatus.IN_ERROR, note=f"Nothing to observe on {self.id}"))

        self.rx_observable = rx.pipe(
            self._rx_prefilter(o),
            rx.filter(lambda e: not self.paused),
            rx.map(emit_raw_fun(self.id)),
            publish(get_last_emit(self.id))
        )

        self._set_require()
        self._rx_require = rx.pipe(
            self._rx_require,
            rx.debounce(0.1),
            rx.distinct_until_changed,
            publish()
        )

        def status(t: tuple[tuple[tuple[ObservableEmit, bool], RawEmit], ObservableEmit]) -> RawEmit:
            (((device_status, paused), driver_status), require_status) = t
            log.debug(f"evaluating observable.status({self.id}, {device_status}, {paused}, {driver_status}, "
                      f"{require_status})")
            if not device_status.enumValue == Status.RUNNING:
                return RawEmit(enumValue=device_status.enumValue)
            if paused:
                return RawEmit(enumValue=Status.PAUSED)
            if driver_status.enumValue in {DriverStatus.RUNNING, DriverStatus.PROGRAM_RUNNING,
                                           DriverStatus.SCHEDULE_RUNNING}:
                return require_status
            if driver_status.enumValue in {DriverStatus.IN_ERROR, DriverStatus.CLOSING}:
                return RawEmit(enumValue=Status.ERROR, note=driver_status.note)
            return RawEmit(self.status_id, Status.INITIALIZING)

        self.rx_status_observable = rx.pipe(
            self.device.rx_status_observable,
            rx.combine_latest(self._rx_paused),
            rx.combine_latest(s),
            rx.combine_latest(self._rx_require),
            rx.map(status),
            rx.distinct_until_changed,
            rx.map(emit_raw_fun(self.status_id)),
            publish()
        )

    def _set_require(self):
        pass

    async def start(self) -> None:
        log.info(f"doing observable.start({self.id})")
        assert self.enabled()
        if self.driver:
            await self.driver.start()

        def throw(txt: str):
            async def err(ex: Exception):
                print(f"!!! {txt} {self.id}", ex)
                log.error(f"{txt} {self.id}", exc_info=ex)
            return err

        def p(txt: str):
            async def _p(e):
                print(f"!!! {txt} {self.id}", e)
            return _p

        for t, o in [
            ("rx_status", self.rx_status_observable),
            ("rx_require", self._rx_require),
            ("rx", self.rx_observable)
        ]:
            self._disposables.append(await o.subscribe_async(throw=throw(t)))
            self._disposables.append(await o.connect())

    async def stop(self) -> None:
        log.info(f"doing observable.stop({self.id})")
        if self.driver:
            await self.driver.stop()
        for d in self._disposables:
            await d.dispose_async()
        self._disposables = []

    async def close(self) -> None:
        log.info(f"doing observable.close({self.id})")
        await self._rx_paused.aclose()

    async def measurement(self, value: float, note: str = None) -> None:
        assert self.enabled()
        raise Exception("Measurement not support for this observable")

    async def set_value(self, value: float | str | RawEmit, note: str = None):
        assert self.enabled()
        raise Exception("Set_value not support for this observable")

    async def add(self, value: float, note: str = None) -> None:
        assert self.enabled()
        raise Exception("Add not support for this observable")

    async def reset(self, note: str = None) -> None:
        assert self.enabled()
        raise Exception("Reset not support for this observable")

    async def fire(self, value: str | RawEmit, note: str = None):
        assert self.enabled()
        raise Exception("Set_value not support for this observable")

    def _driver(self) -> Driver:
        return self.driver or self.device.driver

    def _rx_compare(self, compare_with: Optional[float], f: Callable[[float, float], bool], enumValue: str,
                    note: str) -> Optional[rx.AsyncObservable[RawEmit]]:
        def ff(v: float) -> bool:
            try:
                return f(v, compare_with)
            except Exception:
                return False
        if not compare_with:
            return None
        return rx.pipe(
            self.rx_observable,
            rx.map(
                lambda e: RawEmit(enumValue=Status.RUNNING) if not ff(e.value) else RawEmit(
                    enumValue=enumValue, note=note)
            ),
            rx.distinct_until_changed
        )

    def _rx_compare_enum(self, compare_with: Optional[list[str]], f: Callable[[str, list[str]], bool],
                         note: str) -> Optional[rx.AsyncObservable[RawEmit]]:
        def ff(e: ObservableEmit) -> bool:
            try:
                return f(e.enumValue, compare_with)
            except Exception:
                return False
        if not compare_with:
            return None
        return rx.pipe(
            self.rx_observable,
            rx.map(
                lambda e: RawEmit(enumValue=Status.RUNNING) if not ff(e.enumValue) else RawEmit(
                    enumValue=Status.ALARM, note=note)
            ),
            rx.distinct_until_changed
        )

    def _rx_condition(self, condition: Optional[list[aqt.Condition]], enumValue: Status):
        if condition:
            for c in condition:
                if c.condition:
                    self._rx_require = _rx_require(
                        rx.pipe(
                            as_observable(c.condition, self.device.id),
                            rx.map(
                                lambda e: RawEmit(enumValue=enumValue, note=c.description) if e.value or e.enumValue
                                else RawEmit(enumValue=Status.RUNNING))
                        ),
                        self._rx_require
                    )


class _ValueObservable[MO: aqt.ValueObservable](Observable[MO]):

    def _set_require(self):
        require = self.m_observable.require
        if require:
            self._rx_require = _rx_require(
                self._rx_compare(require.warningAbove, lambda v1, v2: v1 > v2, Status.WARNING,
                                 f"Value above {require.warningAbove}"),
                _rx_require(
                    self._rx_compare(require.warningBelow, lambda v1, v2: v1 < v2, Status.WARNING,
                                     f"Value below {require.warningBelow}"),
                    _rx_require(
                        self._rx_compare(require.alarmAbove, lambda v1, v2: v1 > v2, Status.ALARM,
                                         f"Value above {require.alarmAbove}"),
                        _rx_require(
                            self._rx_compare(require.alarmBelow, lambda v1, v2: v1 < v2, Status.ALARM,
                                             f"Value below {require.alarmBelow}"),
                            self._rx_require
                        )
                    )
                )
            )
            self._rx_condition(require.warningConditions, Status.WARNING)
            self._rx_condition(require.alarmConditions, Status.ALARM)


class Measure(_ValueObservable[aqt.Measure]):

    def _rx_prefilter(self, o: rx.AsyncObservable[RawEmit]) -> rx.AsyncObservable[RawEmit]:
        ctl = self.m_observable.emitControl
        precision = self.m_observable.precision
        if ctl or precision:
            if not ctl:
                ctl = aqt.MeasureEmitControl()
            if ctl.decimals is None and precision:
                p = str(precision).find('')
                ctl.decimals = len(str(precision)) - p - 1 if p > -1 else 0
            if not ctl.supressSameLimit and precision:
                ctl.supressSameLimit = precision
        if ctl:
            if ctl.decimals:
                o = rx.pipe(
                    o,
                    rx.map(lambda e: RawEmit(value=round(e.value, int(ctl.decimals))))
                )
            if ctl.atMostEverySecond:
                o = rx.pipe(
                    o,
                    rx.debounce(ctl.atMostEverySecond)
                )
            if not ctl.supressSameLimit:
                ctl.supressSameLimit = 0.000000001

            def supress_fun(e1: RawEmit, e2: RawEmit) -> bool:
                if e1.value is None or e2.value is None:
                    return False
                return abs(e1.value - e2.value) <= ctl.supressSameLimit
            o = rx.pipe(
                o,
                distinct_until_changed(comparer=supress_fun)
            )
        return o

    async def measurement(self, value: float, note: str = None) -> None:
        await self._driver().set(self.m_observable.id, RawEmit(value=value, note=note))


class _SetObservable[MO: aqt.AbstractObservable](Observable[MO]):

    def __init__(self):
        super().__init__()
        #self._set_expr_disposable: Optional[DisposableBase] = None

    async def set_value(self, value: float | str | RawEmit, note: str = None):
        e: RawEmit
        if isinstance(value, float):
            e = RawEmit(value=value, note=note)
        elif isinstance(value, str):
            e = RawEmit(enumValue=value, note=note)
        elif isinstance(value, RawEmit):
            e = value
            if note:
                e.note = note
        else:
            e = RawEmit()
        log.debug(f"doing observable.set_value({self.id},{e})")
        await self._driver().set(self.m_observable.id, e)

    async def start(self) -> None:
        await super().start()
        if self.m_observable.setExpr:
            self._disposables.append(
                await as_observable(self.m_observable.setExpr, self.device.id).subscribe_async(self.set_value)
            )


class Amount(_SetObservable[aqt.Amount], _ValueObservable[aqt.Amount]):

    async def add(self, value: float, note: str = None) -> None:
        log.info(f"doing observable.add({self.id},{value},{note})")

        async def _add(e: ObservableEmit):
            await self.set_value(e.value + value, note)
        await take_first_async(self.rx_observable, _add)

    async def reset(self, note: str = None) -> None:
        log.info(f"doing observable.reset({self.id},{note})")

        async def _reset(e: RawEmit):
            await self.set_value(e.value, note)

        await take_first_async(as_observable(self.m_observable.resetExpr, self.device.id), _reset)


class State(_SetObservable[aqt.State]):

    def _set_require(self):
        require = self.m_observable.require
        if require:
            self._rx_require = _rx_require(
                self._rx_compare_enum(require.alarmIfIn, lambda e, li: e in li,
                                      f"Value in {require.alarmIfIn}"),  # TODO map to names
                _rx_require(
                    self._rx_compare_enum(require.alarmIfIn, lambda e, li: e in li,
                                          f"Value not in {require.alarmIfIn}"),  # TODO map to names
                    AsyncBehaviorSubject(RawEmit(enumValue=Status.RUNNING))
                )
            )
            self._rx_condition(require.warningConditions, Status.WARNING)
            self._rx_condition(require.alarmConditions, Status.ALARM)


class Event(Observable[aqt.Event]):

    async def fire(self, value: str | RawEmit, note: str = None):
        log.info(f"doing observable.fire({self.id},{value},{note})")
        await self.set_value(value, note)

    def _rx_prefilter(self, o: rx.AsyncObservable[RawEmit]) -> rx.AsyncObservable[RawEmit]:
        if self.m_observable.emitControl and self.m_observable.emitControl.debounceValue:
            o = rx.pipe(o, rx.debounce(self.m_observable.emitControl.debounceValue))
        return o
