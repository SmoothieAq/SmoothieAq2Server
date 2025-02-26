import asyncio
import logging
from enum import StrEnum, auto
from typing import Optional, Callable, cast

import aioreactive as rx
from aioreactive import AsyncSubject
from expression.collections import Map, Block
from expression.system import CancellationToken, CancellationTokenSource

from .expression import as_observable
from ..div.emit import RawEmit, ObservableEmit, emit_enum_value, emit_raw_fun, emit_empty, emit_raw
from ..driver.driver import Status as DriverStatus, Driver
from ..model import thing as aqt
from ..util.rxutil import AsyncBehaviorSubject, publish, distinct_until_changed, take_first_async, throw_it, trace
from ..div.time import time

log = logging.getLogger(__name__)


class Status(StrEnum):
    RUNNING = auto()
    SCHEDULE_RUNNING = auto()
    PROGRAM_RUNNING = auto()
    IDLE = auto()
    STEPS_RUNNING = auto()
    WAITING_INPUT = auto()
    PAUSED = auto()
    WARNING = auto()
    ALARM = auto()
    ERROR = auto()
    INITIALIZING = auto()
    DISABLED = auto()
    PLANNED = auto()


def driver_init(driver_ref: aqt.DriverRef, id: str) -> Optional[Driver]:
    if not driver_ref or not driver_ref.id:
        return None
    from ..driver.drivers import get_driver
    driver = get_driver(driver_ref.id)
    path = driver_ref.path or id
    hal = driver_ref.hal
    globalHal = driver_ref.globalHal
    params = Map.of_block(Block(driver_ref.params or []).map(lambda p: (p.key, p.value)))
    return driver.init(path, hal, globalHal, params)


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
        self._rx_status_subject: Optional[rx.AsyncSubject[ObservableEmit]] = None
        self._rx_subject: Optional[rx.AsyncSubject[ObservableEmit]] = None
        self.rx_status_observable: Optional[rx.AsyncObservable[ObservableEmit]] = None
        self.rx_observable: Optional[rx.AsyncObservable[ObservableEmit]] = None
        self.paused: bool = False
        self._rx_paused = AsyncBehaviorSubject(self.paused)
        self._rx_require: rx.AsyncObservable[RawEmit] = AsyncBehaviorSubject(RawEmit(enumValue=Status.RUNNING))
        self._disposables: list[rx.AsyncDisposable] = []
        self.current_value: ObservableEmit = emit_empty(self.id)
        self.current_status: ObservableEmit = emit_empty(self.id)

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
        return self.m_observable.enablement == 'enabled' and self.device.m_device.enablement == 'enabled'

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
        if self.m_observable.expr:
            log.debug(f"observing expression on observable({self.id})")
            o = as_observable(self.m_observable.expr, self.device.id)
            s = AsyncBehaviorSubject(RawEmit(enumValue=Status.RUNNING))
        elif self.m_observable.driver and self.m_observable.driver.id:
            self.driver = driver_init(self.m_observable.driver, self.id)
            log.debug(f"observing own driver({self.driver.id}) on observable({self.id})")
            o = self.driver.rx_observables['A']
            s = self.driver.rx_status_observable
        elif self.device.driver and self.device.driver.rx_observables.__contains__(self.m_observable.id):
            log.debug(f"observing device driver({self.device.driver.id}) on observable({self.id})")
            o = self.device.driver.rx_observables[self.m_observable.id]
            s = self.device.driver.rx_status_observable
        elif isinstance(self, Action) or isinstance(self, Chore):
            self._rx_subject = AsyncBehaviorSubject(RawEmit())
            o = self._rx_subject
            self._rx_status_subject = AsyncBehaviorSubject(RawEmit(enumValue=Status.IDLE))
            s = self._rx_status_subject
        else:
            log.error(f"nothing to observe on observable({self.id})")
            o = AsyncBehaviorSubject(RawEmit())
            s = AsyncBehaviorSubject(RawEmit(enumValue=Status.ERROR, note=f"Nothing to observe on {self.id}"))

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
                return RawEmit(enumValue=device_status.enumValue, note=device_status.note)
            if paused:
                return RawEmit(enumValue=Status.PAUSED)
            if driver_status.enumValue in {Status.IDLE, Status.STEPS_RUNNING, Status.WAITING_INPUT}: # action or chore
                if require_status.enumValue == Status.RUNNING:
                    return  driver_status
                else:
                    return require_status
            if driver_status.enumValue in {DriverStatus.RUNNING, DriverStatus.PROGRAM_RUNNING,
                                           DriverStatus.SCHEDULE_RUNNING}:
                return require_status
            if driver_status.enumValue in {DriverStatus.IN_ERROR, DriverStatus.CLOSING, Status.ERROR}:
                return RawEmit(enumValue=Status.ERROR, note=driver_status.note)
            return RawEmit(enumValue=Status.INITIALIZING)

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

        for t, o in [
            ("rx_status", self.rx_status_observable),
            ("rx_require", self._rx_require),
            ("rx", self.rx_observable)
        ]:
            self._disposables.append(await o.subscribe_async(throw=throw_it(t)))
            self._disposables.append(await o.connect())
        async def set_curr(o: ObservableEmit) -> None: self.current_value = o
        self._disposables.append(await self.rx_observable.subscribe_async(set_curr))
        async def set_status(s: ObservableEmit) -> None: self.current_status = s
        self._disposables.append(await self.rx_status_observable.subscribe_async(set_status))


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
        assert self.enabled() and not self.paused
        raise Exception("Measurement not support for this observable")

    async def set_value(self, value: float | str | RawEmit, note: str = None):
        assert self.enabled() and not self.paused
        raise Exception("Set_value not support for this observable")

    async def add(self, value: float, note: str = None) -> None:
        assert self.enabled() and not self.paused
        raise Exception("Add not support for this observable")

    async def reset(self, note: str = None) -> None:
        assert self.enabled() and not self.paused
        raise Exception("Reset not support for this observable")

    async def fire(self, value: str | RawEmit, note: str = None):
        assert self.enabled() and not self.paused
        raise Exception("Set_value not support for this observable")

    async def do_action(self):
        assert self.enabled() and not self.paused
        raise Exception("do_action not support for this observable")

    async def async_do_action(self):
        assert self.enabled() and not self.paused
        raise Exception("async_do_action not support for this observable")

    async def start_chore(self, timeout: Optional[float] = None):
        assert self.enabled() and not self.paused
        raise Exception("start_chore not support for this observable")

    async def done(self):
        assert self.enabled() and not self.paused
        raise Exception("done not support for this observable")

    async def skip(self):
        assert self.enabled() and not self.paused
        raise Exception("skip not support for this observable")

    async def delay(self):
        assert self.enabled() and not self.paused
        raise Exception("skip not support for this observable")

    async def input(self, stedId: str, input: RawEmit):
        assert self.enabled() and not self.paused
        raise Exception("input not support for this observable")

    async def cancel(self):
        assert self.enabled() and not self.paused
        raise Exception("cancel not support for this observable")

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
                p = str(precision).find('.')
                ctl.decimals = len(str(precision)) - p - 1 if p > -1 and precision <0.9999 else 0
            if not ctl.supressSameLimit and precision:
                ctl.supressSameLimit = precision
        if ctl:
            if ctl.decimals is not None:
                def f(e):
                    v = round(e.value, int(ctl.decimals))
                    return RawEmit(value=round(e.value, int(ctl.decimals)))
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
        assert self.enabled() and not self.paused
        await self._driver().set(self.m_observable.id, RawEmit(value=value, note=note))


class SetObservable[MO: aqt.AbstractObservable](Observable[MO]):

    def __init__(self):
        super().__init__()
        #self._set_expr_disposable: Optional[DisposableBase] = None

    async def set_value(self, value: float | str | RawEmit, note: str = None):
        assert self.enabled() and not self.paused
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


class Amount(SetObservable[aqt.Amount], _ValueObservable[aqt.Amount]):

    async def add(self, value: float, note: str = None) -> None:
        assert self.enabled() and not self.paused
        log.info(f"doing observable.add({self.id},{value},{note})")

        async def _add(e: ObservableEmit):
            await self.set_value(e.value + value, note)
        await take_first_async(self.rx_observable, _add)

    async def reset(self, note: str = None) -> None:
        assert self.enabled() and not self.paused
        log.info(f"doing observable.reset({self.id},{note})")

        async def _reset(e: RawEmit):
            await self.set_value(e.value, note)

        await take_first_async(as_observable(self.m_observable.resetExpr, self.device.id), _reset)

    async def start(self) -> None:
        await super().start()
        if self.m_observable.addExpr:
            async def add(re: RawEmit) -> None:
                log.debug(f"doing observable.addExpr({self.id},{re.value},{re.note})")

                async def _add(e: ObservableEmit):
                    await self.set_value(e.value + re.value, re.note)

                await take_first_async(self.rx_observable, _add)

            self._disposables.append(
                await as_observable(self.m_observable.addExpr, self.device.id).subscribe_async(add)
            )


class State(SetObservable[aqt.State]):

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
        assert self.enabled() and not self.paused
        log.info(f"doing observable.fire({self.id},{value},{note})")
        await self.set_value(value, note)

    def _rx_prefilter(self, o: rx.AsyncObservable[RawEmit]) -> rx.AsyncObservable[RawEmit]:
        if self.m_observable.emitControl and self.m_observable.emitControl.debounceValue:
            o = rx.pipe(o, rx.debounce(self.m_observable.emitControl.debounceValue))
        return o

class ActionOrChore[MO: aqt.AbstractObservable](Observable[MO]):

    def __init__(self):
        super().__init__()
        self.steps_task: Optional[asyncio.Task] = None

    async def start(self):
        await super().start()
        await self.rx_status_asend(Status.IDLE)

    async def cancel(self):
        assert self.enabled() and not self.paused
        assert self.steps_task
        await self.rx_status_asend(Status.ERROR,f"Cancelled")
        self.steps_task.cancel()
        self.steps_task = None

    async def rx_asend(self, enumValue: str, note: Optional[str] = None, value: float = time()):
        await self._rx_subject.asend(emit_raw(self.id, RawEmit(value=value, enumValue=enumValue, note=note)))

    async def rx_status_asend(self, enumValue: str, note: Optional[str] = None):
        await self._rx_status_subject.asend(emit_raw(self.id, RawEmit(enumValue=enumValue, note=note)))

    async def _do_steps(self):
        await self.rx_status_asend(Status.STEPS_RUNNING)
        from .step import do_steps
        complete = await do_steps(self.m_observable.steps, self.device, self)
        if complete:
            await self.rx_asend("done")
        await self.rx_status_asend(Status.IDLE)

    def _do_action(self, defaultTimeout: float, timeout: Optional[float] = None):
        to = timeout or self.m_observable.timeout or defaultTimeout
        async def __do_action():
            try:
                task = asyncio.create_task(self._do_steps())
                if not self.steps_task:
                    self.steps_task = task
                await asyncio.wait_for(task, to)
            except TimeoutError:
                await self.rx_status_asend(Status.ERROR, f"Timeout")
            except Exception as e:
                log.exception(f"Exception in do_action")
                raise e
            finally:
                self.steps_task = None
        return __do_action()

    async def _async_do_action(self, timeout: Optional[float] = None):
        assert not self.steps_task

        self.steps_task = asyncio.create_task(self._do_action(20, timeout))


class Chore(ActionOrChore[aqt.Chore]):

    def __init__(self):
        super().__init__()
        self.inputs: Optional[dict[str,AsyncBehaviorSubject[RawEmit]]] = None # stepId -> input obs
        self._rx_plan: Optional[rx.AsyncDisposable] = None

    async def start(self):
        await super().start()
        from .plan import plan
        self._rx_plan = await plan(self)

    async def stop(self) -> None:
        await super().stop()
        if self._rx_plan:
            await self._rx_plan.dispose_async()

    async def _replan(self):
        if self._rx_plan:
            await self._rx_plan.dispose_async()
        from .plan import plan
        self._rx_plan = await plan(self)

    async def cancel(self):
        await super().cancel()
        self.inputs = None

    async def start_chore(self, timeout: Optional[float] = None):
        assert self.enabled() and not self.paused
        assert not self.steps_task
        assert self.m_observable.steps

        if self._rx_plan:
            await self._rx_plan.dispose_async()
        log.info(f"doing observable.start_chore({self.id})")
        await self._async_do_action(timeout)
        from .plan import plan
        self._rx_plan = await plan(self)

    async def input(self, stedId: str, input: RawEmit):
        assert self.enabled() and not self.paused
        assert self.inputs and self.inputs.__contains__(stedId)
        log.info(f"doing observable.input({self.id})")
        await self.inputs[stedId].asend(input)

    async def done(self):
        assert self.enabled() and not self.paused
        assert not self.steps_task
        assert not self.m_observable.steps

        log.info(f"doing observable.done({self.id})")
        await self.rx_asend("done")
        if not self.current_status.enumValue == Status.IDLE:
            await self.rx_status_asend(Status.IDLE)
        from .plan import plan
        self._rx_plan = await plan(self)

    async def skip(self):
        assert self.enabled() and not self.paused
        if self.steps_task:
            await self.cancel()
        log.info(f"doing observable.skip({self.id})")
        await self.rx_asend("skip")
        if not self.current_status.enumValue == Status.IDLE:
            await self.rx_status_asend(Status.IDLE)
        from .plan import plan
        self._rx_plan = await plan(self)

    async def delay(self):
        assert self.enabled() and not self.paused
        if self.steps_task:
            await self.cancel()
        log.info(f"doing observable.delay({self.id})")
        await self.rx_asend("delay", value=self.current_value.value)
        if not self.current_status.enumValue == Status.IDLE:
            await self.rx_status_asend(Status.IDLE)
        from .plan import plan
        self._rx_plan = await plan(self)


class Action(ActionOrChore[aqt.Action]):

    async def do_action(self, timeout: Optional[float] = None):
        assert self.enabled() and not self.paused
        assert not self.steps_task
        assert not self.m_observable.runAsync

        log.info(f"doing observable.do_action({self.id})")
        self.steps_task = asyncio.create_task(self._do_action(2, timeout))
        await self.steps_task

    async def async_do_action(self, timeout: Optional[float] = None):
        assert self.enabled() and not self.paused
        assert not self.m_observable.runAsync

        log.info(f"doing observable.async_do_action({self.id})")
        await self._async_do_action(timeout)
