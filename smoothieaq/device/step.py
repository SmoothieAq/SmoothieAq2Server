import asyncio
from asyncio import sleep
from typing import Type

from .device import Device
from .devices import observables, devices
from .observable import *
from ..model import step as aqs
from ..model.step import *
from ..util.rxutil import take_first, await_first

log = logging.getLogger(__name__)


async def do_steps(steps: list[aqs.Step], device: Device, action: ActionOrChore) -> bool:
    async def do_step(step: aqs.Step) -> bool:  # if false, then break
        def find_observable[T](t: Type[T], id: str) -> T:
            idx = id[1:] if id[0] == ':' else id
            o = device.observables[id] if idx.find(':') == -1 else observables[idx]
            if not isinstance(o, t):
                raise KeyError
            return o

        if isinstance(step, ActionStep):
            await find_observable(Action, step.actionRef).do_action()
        elif isinstance(step, EnableStep):
            pass
        elif isinstance(step, DisableStep):
            pass
        elif isinstance(step, PauseStep):
            try:
                await find_observable(Observable, step.observableRef).pause()
            except KeyError:
                await devices[step.observableRef].pause()
        elif isinstance(step, UnpauseStep):
            try:
                await find_observable(Observable, step.observableRef).pause()
            except KeyError:
                await devices[step.observableRef].pause()
        elif isinstance(step, PollStep):
            if step.observableRef.find(':') > -1: raise KeyError
            await devices[step.observableRef].poll()
        elif isinstance(step, ResetValueStep):
            await find_observable(Amount, step.observableRef).reset()
        elif isinstance(step, SetValueStep):
            async def _set_value(e: RawEmit):
                await find_observable(SetObservable, step.observableRef).set_value(e)

            await take_first_async(as_observable(step.expr, device.id), _set_value)
        elif isinstance(step, AddValueStep):
            async def _add_value(e: RawEmit):
                await find_observable(Amount, step.observableRef).add(e.value, e.note)

            await take_first_async(as_observable(step.expr, device.id), _add_value)
        elif isinstance(step, FireStep):
            async def _fire(e: RawEmit):
                await find_observable(Event, step.observableRef).fire(e)

            await take_first_async(as_observable(step.expr, device.id), _fire)
        elif isinstance(step, AssertStep):
            e = await await_first(as_observable(step.condition, device.id))
            if (not e.value and not e.enumValue) or e.enumValue in {'false', 'off'}:
                log.error(f"Assertion step failed on {action.id} {step.id}")
                await action.rx_status_asend(DriverStatus.IN_ERROR, f"{step.id} assertion error")
                return False
            return True
        elif isinstance(step, WaitStep):
            # sleep in seconds to allow cancel
            await sleep(step.timeToWait)
        elif isinstance(step, WaitUntilStep):
            pass  # TODO
        elif isinstance(step, StopIfStep):
            e = await await_first(as_observable(step.condition, device.id))
            return not ((not e.value and not e.enumValue) or e.enumValue in {'false', 'off'})
        elif isinstance(step, ListStep):
            if not do_steps(step.steps, device, action):
                return False
        elif isinstance(step, ParallelStep):
            for complete in await asyncio.gather(*[wrap_do_step(pstep) for pstep in step.steps]):
                if not complete:
                    return False
        elif isinstance(step, ProgramStep):
            pass  # TODO
        elif (isinstance(step, InputStep) or isinstance(step, DoneStep)) and isinstance(action, Chore):
            if not action.inputs:
                action.inputs = {}
            action.inputs[step.id] = AsyncBehaviorSubject(RawEmit(enumValue='-'))
            await await_first(rx.pipe(action.inputs[step.id], rx.filter(lambda e: not e.enumValue == '-')))
            # todo InputSet.autoAcceptExpr
            await action.rx_status_asend(Status.STEPS_RUNNING, f"{step.id} {step.description}")
        else:
            raise KeyError
        return True

    async def wrap_do_step(step: aqs.Step) -> bool:
        try:
            log.debug(f"{action.id} doing {step.id}")
            await action.rx_status_asend(Status.STEPS_RUNNING, f"{step.id} {step.description}")
            return await do_step(step)
        except Exception as e:
            log.exception(f"{action.id} {step.id}")
            await action.rx_status_asend(Status.ERROR, f"{step.id} {e=}")
            return False

    for step in steps:
        if not await wrap_do_step(step):
            return False
    return True

