from typing import Callable

import reactivex as rx
import reactivex.operators as op

from smoothieaq.div.emit import RawEmit
from . import devices as dv
from ..model import expression as aqe

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
        value=float(e1.value > e2.value if e1.value or e2.value else e1.enumValue > e2.enumValu)),
    aqe.BinaryOp.GE: lambda e1, e2: RawEmit(
        value=float(e1.value >= e2.value if e1.value or e2.value else e1.enumValue >= e2.enumValu)),
    aqe.BinaryOp.LT: lambda e1, e2: RawEmit(
        value=float(e1.value < e2.value if e1.value or e2.value else e1.enumValue < e2.enumValu)),
    aqe.BinaryOp.LE: lambda e1, e2: RawEmit(
        value=float(e1.value == e2.value if e1.value or e2.value else e1.enumValue == e2.enumValu)),
    aqe.BinaryOp.ADD: lambda e1, e2: RawEmit(value=e1.value + e2.value),
    aqe.BinaryOp.SUBTRACT: lambda e1, e2: RawEmit(value=e1.value - e2.value),
    aqe.BinaryOp.MULTIPLY: lambda e1, e2: RawEmit(value=e1.value * e2.value),
    aqe.BinaryOp.DIVIDE: lambda e1, e2: RawEmit(value=e1.value / e2.value), }
_rxOps0: dict[aqe.RxOp0, Callable[[], Callable[[rx.Observable[RawEmit]], rx.Observable[RawEmit]]]] = {
    aqe.RxOp0.DISTINCT: lambda: op.distinct_until_changed(comparer=lambda e1, e2: (
        e1.enumValue == e2.enumValue if e1.enumValue or e2.enumValue else (
                (e1.value is None and e2.value is None) or abs(e1.value - e2.value) < 0.0001
        )
    ))
}
_rxOps1: dict[aqe.RxOp1, Callable[[float], Callable[[rx.Observable[RawEmit]], rx.Observable[RawEmit]]]] = {
    aqe.RxOp1.DEBOUNCE: lambda a: op.debounce(a),
    aqe.RxOp1.THROTTLE: lambda a: op.throttle_with_timeout(a)
}


def find_rx_observables(expr: aqe.Expr, device_id: str) -> dict[str, rx.Observable[RawEmit]]:
    rx_observables: dict[str, rx.Observable] = {}

    def find_label(prefix: str, i: int = 1) -> str:
        id = prefix + str(i)
        return id if not rx_observables.__contains__(id) else find_label(prefix, i + 1)

    def find(expr: aqe.Expr) -> None:
        if isinstance(expr, aqe.UnaryOpExpr):
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
            rx_observables[expr._label] = as_observable(expr.expr, device_id).pipe(_rxOps0[expr.op]())
        elif isinstance(expr, aqe.RxOp1Expr):
            if not expr._label:
                expr._label = find_label(expr.op)
            rx_observables[expr._label] = as_observable(expr.expr, device_id).pipe(_rxOps1[expr.op](expr.arg))
        elif isinstance(expr, aqe.ObservableExpr):
            id = expr.observableRef if expr.observableRef.find(":") > 0 else device_id + ":" + expr.observableRef
            if not rx_observables.__contains__(id):
                def get_observable(s) -> rx.Observable[RawEmit]:
                    o = dv.get_rx_observable(id)
                    if not o:
                        #  log error
                        return rx.subject.BehaviorSubject(RawEmit())
                    return o

                rx_observables[id] = rx.defer(get_observable)

    find(expr)
    return rx_observables


def evaluate(expr: aqe.Expr, vals: dict[str, RawEmit]) -> RawEmit:
    def eval(expr: aqe.Expr) -> RawEmit:
        if isinstance(expr, aqe.UnaryOpExpr):
            return _unaries[expr.op](eval(expr.expr))
        elif isinstance(expr, aqe.BinaryOpExpr):
            return _binaries[expr.op](eval(expr.expr1), eval(expr.expr2))
        elif isinstance(expr, aqe.IfExpr):
            return eval(expr.thenExpr) if eval(expr.ifExpr).value else eval(expr.elseExpr)
        elif isinstance(expr, aqe.WhenExpr):
            for when in expr.whens:
                if eval(when.ifExpr).value:
                    return eval(when.thenExpr)
            return eval(expr.elseExpr)
        elif isinstance(expr, aqe.RxOp0Expr):
            return vals[expr._label]
        elif isinstance(expr, aqe.RxOp1Expr):
            return vals[expr._label]
        elif isinstance(expr, aqe.ObservableExpr):
            return vals[expr.observableRef]
        elif isinstance(expr, aqe.EnumValueExpr):
            return RawEmit(enumValue=expr.enumValue)
        elif isinstance(expr, aqe.ValueExpr):
            return RawEmit(value=expr.value)
        else:
            return RawEmit()

    return eval(expr)


def as_observable(expr: aqe.Expr, device_id: str) -> rx.Observable[RawEmit]:
    rx_observables = find_rx_observables(expr, device_id)
    observable_ids = list(rx_observables.keys())
    if isinstance(expr, aqe.RxOp0Expr):
        return rx_observables[expr._label]
    if isinstance(expr, aqe.RxOp1Expr):
        return rx_observables[expr._label]
    if isinstance(expr, aqe.ObservableExpr):
        return rx_observables[expr.observableRef]
    if len(rx_observables) == 0:
        return rx.subject.BehaviorSubject(evaluate(expr, {}))
    if len(rx_observables) == 1:
        return rx_observables[observable_ids[0]].pipe(op.map(lambda e: evaluate(expr, {observable_ids[0]: e})))
    if len(rx_observables) == 2:
        return rx.combine_latest(rx_observables[observable_ids[0]], rx_observables[observable_ids[1]]).pipe(
            op.map(lambda t: evaluate(expr, {observable_ids[0]: t[0], observable_ids[1]: t[1]})))
    if len(rx_observables) == 3:
        return rx.combine_latest(
            rx_observables[observable_ids[0]], rx_observables[observable_ids[1]], rx_observables[observable_ids[2]]
        ).pipe(op.map(
            lambda t: evaluate(expr, {observable_ids[0]: t[0], observable_ids[1]: t[1], observable_ids[2]: t[2]}))
        )
    if len(rx_observables) == 4:
        return rx.combine_latest(
            rx_observables[observable_ids[0]], rx_observables[observable_ids[1]], rx_observables[observable_ids[2]],
            rx_observables[observable_ids[3]]
        ).pipe(
            op.map(lambda t: evaluate(expr,
                                      {observable_ids[0]: t[0], observable_ids[1]: t[1], observable_ids[2]: t[2],
                                       observable_ids[3]: t[3]})))
    #  log error
    return rx.subject.BehaviorSubject(RawEmit())
