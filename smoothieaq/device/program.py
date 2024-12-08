import datetime
import logging
import math
import random
from asyncio import sleep
from dataclasses import dataclass

from expression.collections import Block
from expression.system import CancellationToken

from ..device.device import Device
from ..device.scheduleat import time_length
from ..div.time import time as div_time, duration
from ..model.thing import Program, ProgramValue
from ..util.rxutil import ix

log = logging.getLogger(__name__)


@dataclass
class _SubProgram:
    type: str
    values: Block[tuple[str, float, float]]
    length: float
    step: float
    arg: float


def _sub_programs(program: Program) -> Block[_SubProgram]:
    values: Block[tuple[str, float]] = Block.of_seq(ix(program.values).map(lambda v: (v.id, v.value)))
    sub_programs: Block[_SubProgram] = Block.empty()
    length = time_length(program.length).total_seconds()
    in_tr = program.inTransition or program.transition
    out_tr = program.outTransition or program.transition
    if in_tr:
        in_length = time_length(in_tr.length).total_seconds()
        sub_programs += Block.of(_SubProgram(in_tr.type, values.map(lambda t: (t[0], 0., t[1])), in_length,
                                             in_tr.step, in_tr.arg))
        length -= in_length
    if out_tr:
        length -= time_length(out_tr.length).total_seconds()
    sub_programs += Block.of(_SubProgram("steady", values.map(lambda t: (t[0], t[1], t[1])), length, 0, 0))
    if out_tr:
        out_length = time_length(out_tr.length).total_seconds()
        sub_programs += Block.of(_SubProgram(out_tr.type, values.map(lambda t: (t[0], t[1], 0.)), out_length,
                                             out_tr.step, out_tr.arg))
    return sub_programs


def derived_logistic(x: float, k: float) -> float:
    # https://en.wikipedia.org/wiki/Logistic_function
    ex = math.exp(-k * x)
    return (ex / (1 + ex)) * (1 / (1 + ex))


def logistic(x: float, k: float) -> float:
    # https://en.wikipedia.org/wiki/Logistic_function
    return 1 / (1 + math.exp(-k * x))


def logit(x: float, k: float) -> float:
    # https://en.wikipedia.org/wiki/Logit
    return 1 / k * math.log(x / (1 - x))


async def do_program(device: Device, program: Program, wanted_start_time: float,
                     cancellation: CancellationToken) -> None:
    start_time = div_time()
    assert start_time >= wanted_start_time
    min_wait = random.random() * 4 + 6

    async def run_on_program(value: ProgramValue):
        log.info(f"Doing on-program on device {device.id}")
        await device.observables[value.id].set_value("on")
        length = time_length(program.length).total_seconds()
        while True:
            so_far = div_time() - wanted_start_time
            rest = length - so_far
            if cancellation.is_cancellation_requested:
                return
            if rest < 0.1:
                break
            await sleep(duration(min(min_wait, rest)))
        await device.observables[value.id].set_value("off")

    async def run_sub_program(sub_program: _SubProgram, wanted_start_time: float):
        # print("$$1", datetime.datetime.fromtimestamp(wanted_start_time), datetime.datetime.fromtimestamp(div_time()))

        match sub_program.type:
            case "steady":
                wait_fun = lambda f, s, e: sub_program.length * (1 - f)
                val_fun = lambda f, s, e: e
            case "linear":
                wait_fun = lambda f, s, e: sub_program.step / (abs(e - s) / sub_program.length)
                val_fun = lambda f, s, e: s + (e - s) * f
            case "s":
                dl = lambda f: derived_logistic((f - 0.5) * 10, sub_program.arg or 1)
                wait_fun = lambda f, s, e: (sub_program.step / ((e - s) * max(0.05, dl(f)) / sub_program.length * 10))
                val_fun = lambda f, s, e: s + (e - s) * logistic((f - 0.5) * 10, sub_program.arg or 1)
            case _:
                log.error(f"Unknown sub-program type {sub_program.type} on device {device.id}")
                return

        log.info(f"Doing sub-program on device {device.id}")
        while True:
            now = div_time()
            so_far = now - wanted_start_time
            rest = sub_program.length - so_far
            if rest < 0.1:
                break

            fraction = so_far / sub_program.length
            wait = min(rest, max(0.1, sub_program.values.map(lambda v: wait_fun(fraction, v[1], v[2])).reduce(min)))
            assert wait > 0.01
            to = now + wait
            # print("$$2", wait)
            while now < to:
                if cancellation.is_cancellation_requested:
                    return
                # print("$$2", wait, to - now)
                await sleep(duration(min(min_wait, to - now)))
                now = div_time()

            fraction = (now - wanted_start_time) / sub_program.length
            for v in sub_program.values:
                # print("$$3", v, fraction, val_fun(fraction, v[1], v[2]),
                #      logistic((fraction - 0.5) * 10, sub_program.arg or 1))
                await device.observables[v[0]].set_value(val_fun(fraction, v[1], v[2]))

        for v in sub_program.values:
            # print("$$3", v, v[2])
            await device.observables[v[0]].set_value(v[2])

    log.debug(f"Doing program on device {device.id}")
    if len(program.values) == 1 and program.values[0].enumValue == "on":
        await run_on_program(program.values[0])
    else:
        sub_programs = _sub_programs(program)
        sub_so_far = 0
        for sub_program in sub_programs:
            if cancellation.is_cancellation_requested:
                break
            if wanted_start_time + sub_so_far + sub_program.length > start_time:
                await run_sub_program(sub_program, wanted_start_time + sub_so_far)
            sub_so_far += sub_program.length
