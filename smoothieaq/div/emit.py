from ..div import time
from dataclasses import dataclass
from typing import Optional, Callable


class Emit:
    pass


@dataclass
class RawEmit(Emit):
    value: Optional[float] = None
    enumValue: Optional[str] = None
    note: Optional[str] = None


@dataclass
class ObservableEmit(RawEmit):
    observable_id: str = ""
    stamp: Optional[float] = None


def emit_raw(id: str, raw_emit: RawEmit) -> ObservableEmit:
    return ObservableEmit(
        observable_id=id,
        value=raw_emit.value,
        enumValue=raw_emit.enumValue,
        note=raw_emit.note,
        stamp=time.time()
    )


def emit_empty(id: str) -> ObservableEmit:
    return ObservableEmit(
        observable_id=id,
        note="Empty default",
        stamp=time.time()
    )


def emit_raw_fun(id: str) -> Callable[[RawEmit], ObservableEmit]:
    return lambda e: emit_raw(id, e)


def emit_value(id: str, value: float, note=None) -> ObservableEmit:
    return ObservableEmit(
        observable_id=id,
        value=value,
        note=note,
        stamp=time.time()
    )


def emit_enum_value(id: str, enum_value: str, note=None) -> ObservableEmit:
    return ObservableEmit(
        observable_id=id,
        enumValue=enum_value,
        note=note,
        stamp=time.time()
    )


def stamp_to_transport(stamp: float) -> int:
    return int(stamp * 10)


def emit_to_transport(emit: ObservableEmit) -> list[str]:
    stamp = stamp_to_transport(emit.stamp)
    value = None if emit.value is None else str(emit.value)
    if emit.note:
        return [emit.observable_id, stamp, value, emit.enumValue, emit.note]
    elif emit.enumValue:
        return [emit.observable_id, stamp, value, emit.enumValue]
    else:
        return [emit.observable_id, stamp, value]
