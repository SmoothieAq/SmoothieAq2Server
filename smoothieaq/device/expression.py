from copy import deepcopy
from typing import Callable, cast

import aioreactive as rx
from expression.collections import Block, Map

from ..div.emit import RawEmit
from . import devices as dv
from ..div.enums import convert
from ..model import expression as aqe
from ..util.rxutil import distinct_until_changed, sample, AsyncBehaviorSubject, ix, trace

_unaries: dict[aqe.UnaryOp, Callable[[RawEmit], RawEmit]] = {
    aqe.UnaryOp.NOT: lambda e: RawEmit(value=0.0 if e.value else 1.0),
    aqe.UnaryOp.NEGATE: lambda e: RawEmit(value=-e.value)
}
_binaries: dict[aqe.BinaryOp, Callable[[RawEmit, RawEmit], RawEmit]] = {
    aqe.BinaryOp.AND: lambda e1, e2: RawEmit(value=float(e1.value and e2.value)),
    aqe.BinaryOp.OR: lambda e1, e2: RawEmit(value=float(e1.value or e2.value)),
    # aqe.BinaryOp.XOR: lambda e1, e2: RawEmit(value=e1.value xor e2.value),
    aqe.BinaryOp.EQ: lambda e1, e2: RawEmit(
        value=float(e1.value == e2.value if e1.value or e2.value else e1.enumValue == e2.enumValu)),
    aqe.BinaryOp.NE: lambda e1, e2: RawEmit(
        value=float(e1.value != e2.value if e1.value or e2.value else e1.enumValue != e2.enumValu)),
    aqe.BinaryOp.GT: lambda e1, e2: RawEmit(
        value=float(e1.value > e2.value if e1.value and e2.value
                    else e1.enumValue is not None and e2.enumValue is not None and e1.enumValue > e2.enumValu)),
    aqe.BinaryOp.GE: lambda e1, e2: RawEmit(
        value=float(e1.value >= e2.value if e1.value and e2.value
                    else e1.enumValue is not None and e2.enumValue is not None and e1.enumValue >= e2.enumValu)),
    aqe.BinaryOp.LT: lambda e1, e2: RawEmit(
        value=float(e1.value < e2.value if e1.value and e2.value
                    else e1.enumValue is not None and e2.enumValue is not None and e1.enumValue < e2.enumValu)),
    aqe.BinaryOp.LE: lambda e1, e2: RawEmit(
        value=float(e1.value <= e2.value if e1.value and e2.value
                    else e1.enumValue is not None and e2.enumValue is not None and e1.enumValue == e2.enumValu)),
    aqe.BinaryOp.ADD: lambda e1, e2: RawEmit(value=e1.value + e2.value) if (
        e1.value is not None and e2.value is not None) else RawEmit(),
    aqe.BinaryOp.SUBTRACT: lambda e1, e2: RawEmit(value=e1.value - e2.value) if (
        e1.value is not None and e2.value is not None) else RawEmit(),
    aqe.BinaryOp.MULTIPLY: lambda e1, e2: RawEmit(value=e1.value * e2.value) if (
        e1.value is not None and e2.value is not None) else RawEmit(),
    aqe.BinaryOp.DIVIDE: lambda e1, e2: RawEmit(value=e1.value / e2.value) if (
        e1.value is not None and e2.value is not None) else RawEmit(),
}
_rxOps0: dict[aqe.RxOp0, Callable[[], Callable[[rx.AsyncObservable[RawEmit]], rx.AsyncObservable[RawEmit]]]] = {
    aqe.RxOp0.DISTINCT: lambda: distinct_until_changed(comparer=lambda e1, e2: (
        e1.enumValue == e2.enumValue if e1.enumValue or e2.enumValue else (
                (e1.value is None and e2.value is None) or abs(e1.value - e2.value) < 0.0001
        )
    ))
}
_rxOps1: dict[aqe.RxOp1, Callable[[float], Callable[[rx.AsyncObservable[RawEmit]], rx.AsyncObservable[RawEmit]]]] = {
    aqe.RxOp1.DEBOUNCE: lambda a: rx.debounce(a),
    #aqe.RxOp1.THROTTLE: lambda a: op.throttle_with_timeout(a)
}


def find_rx_observables(expr: aqe.Expr, device_id: str) -> dict[str, rx.AsyncObservable[RawEmit]]:
    rx_observables: dict[str, rx.AsyncObservable] = {}

    def find_label(prefix: str, i: int = 1) -> str:
        id = prefix + str(i)
        return id if not rx_observables.__contains__(id) else find_label(prefix, i + 1)

    def find(expr: aqe.Expr) -> None:
        if isinstance(expr, aqe.UnaryOpExpr):
            find(expr.expr)
        elif isinstance(expr, aqe.ConvertExpr):
            find(expr.expr)
        elif isinstance(expr, aqe.BinaryOpExpr):
            find(expr.expr1)
            find(expr.expr2)
        elif isinstance(expr, aqe.IfExpr):
            find(expr.ifExpr)
            find(expr.thenExpr)
            find(expr.elseExpr)
        elif isinstance(expr, aqe.WhenExpr):
            for w in expr.whens:
                find(w.ifExpr)
                find(w.thenExpr)
            if expr.elseExpr:
                find(expr.elseExpr)
        elif isinstance(expr, aqe.RxOp0Expr):
            if not expr._label:
                expr._label = find_label(expr.op)
            rx_observables[expr._label] = rx.pipe(as_observable(expr.expr, device_id), _rxOps0[expr.op]())
        elif isinstance(expr, aqe.RxOp1Expr):
            if not expr._label:
                expr._label = find_label(expr.op)
            rx_observables[expr._label] = rx.pipe(as_observable(expr.expr, device_id), _rxOps1[expr.op](expr.arg))
        elif isinstance(expr, aqe.OnExpr):
            if not expr._label:
                expr._label = find_label("on")
            rx_observables[expr._label] = rx.pipe(
                as_observable(expr.thenExpr, device_id),
                sample(as_observable(expr.onExpr, device_id))
            )
        elif isinstance(expr, aqe.ObservableExpr):
            id = expr.observableRef if expr.observableRef.find(":") > 0 else device_id + ":" + expr.observableRef
            if not rx_observables.__contains__(id):
                def get_observable() -> rx.AsyncObservable[RawEmit]:
                    elms = id.split('--')
                    if len(elms) == 2: # Chore input
                        from .observable import Chore
                        do = cast(Chore, dv.get_observable(elms[0]))
                        if not do or not do.inputs or not do.inputs[elms[1]]:
                            from .observable import log
                            note = f"Could not find step {elms[1]} in chore {elms[0]} used in expression on device {device_id}"
                            log.error(note)
                            return AsyncBehaviorSubject(RawEmit(note=note))
                        return do.inputs[elms[1]]
                    o = dv.get_rx_observable(id)
                    if not o:
                        from .observable import log
                        note = f"Could not find observable {id} used in expression on device {device_id}"
                        log.error(note)
                        return AsyncBehaviorSubject(RawEmit(note=note))
                    return o

                rx_observables[expr.observableRef] = rx.defer(get_observable)

    find(expr)
    return rx_observables


def evaluate(expr: aqe.Expr, vals: Map[str, RawEmit]) -> RawEmit:
    def eval(expr: aqe.Expr) -> RawEmit:
        try:
            if isinstance(expr, aqe.UnaryOpExpr):
                return _unaries[expr.op](eval(expr.expr))
            if isinstance(expr, aqe.ConvertExpr):
                return RawEmit(value=convert(eval(expr.expr).value, expr.quantity, expr.fromUnit, expr.toUnit))
            if isinstance(expr, aqe.BinaryOpExpr):
                # print(expr.op.name, eval(expr.expr1), eval(expr.expr2), _binaries[expr.op](eval(expr.expr1), eval(expr.expr2)), expr)
                return _binaries[expr.op](eval(expr.expr1), eval(expr.expr2))
            if isinstance(expr, aqe.IfExpr):
                return eval(expr.thenExpr) if eval(expr.ifExpr).value else eval(expr.elseExpr)
            if isinstance(expr, aqe.WhenExpr):
                for when in expr.whens:
                    if eval(when.ifExpr).value:
                        return eval(when.thenExpr)
                return eval(expr.elseExpr)
            if isinstance(expr, aqe.RxOp0Expr):
                return vals[expr._label]
            if isinstance(expr, aqe.RxOp1Expr):
                return vals[expr._label]
            if isinstance(expr, aqe.OnExpr):
                return vals[expr._label]
            if isinstance(expr, aqe.ObservableExpr):
                return vals[expr.observableRef]
            if isinstance(expr, aqe.EnumValueExpr):
                return RawEmit(enumValue=expr.enumValue)
            if isinstance(expr, aqe.ValueExpr):
                return RawEmit(value=expr.value)
            from .observable import log
            log.error(f"Can't handle expression {expr}")
            return RawEmit()
        except Exception as e:
            from .observable import log
            log.error(f"Error evaluating {expr}", exc_info=e)
            return RawEmit(note=f"Error evaluating {expr}")

    return eval(expr)


def as_observable(expr: aqe.Expr, device_id: str) -> rx.AsyncObservable[RawEmit]:
    try:
        rx_observables = find_rx_observables(expr, device_id)
        observable_ids = Block(rx_observables.keys())
        if isinstance(expr, aqe.RxOp0Expr):
            return rx_observables[expr._label]
        if isinstance(expr, aqe.RxOp1Expr):
            return rx_observables[expr._label]
        if isinstance(expr, aqe.OnExpr):
            return rx_observables[expr._label]
        if isinstance(expr, aqe.ObservableExpr):
            return rx_observables[expr.observableRef]
        if len(observable_ids) == 0:
            return AsyncBehaviorSubject(evaluate(expr, Map.empty()))

        def oa(a, ids: Block[str]) -> Map[str, RawEmit]:
            match a:
                case (a1, a2):
                    return oa(a1, ids.take(len(ids) - 1)).add(ids[-1], a2)
                case _:
                    return Map.empty().add(ids[0], a)
        return rx.pipe(
            rx_observables[observable_ids[0]],
            *ix(observable_ids[1:]).map(lambda id: rx.combine_latest(rx_observables[id])),
            rx.map(lambda a: evaluate(expr, oa(a, observable_ids)))
        )
    except Exception as ex:
        from .observable import log
        log.error(f"Expression {expr} on {device_id}", exc_info=ex)
        return AsyncBehaviorSubject(RawEmit())
