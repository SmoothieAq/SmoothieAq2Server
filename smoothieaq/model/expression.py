from dataclasses import dataclass
from typing import Optional, Literal
from typing_extensions import Annotated
from pydantic import Field
from enum import StrEnum, auto


#@dataclass
class UnaryOp(StrEnum):
    NEGATE = auto()
    NOT = auto()

    def __hash__(self):
        return hash(str(self.value))


#@dataclass
class BinaryOp(StrEnum):
    AND = auto()
    OR = auto()
    XOR = auto()
    EQ = auto()
    NE = auto()
    GT = auto()
    GE = auto()
    LT = auto()
    LE = auto()
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()

    def __hash__(self):
        return hash(str(self.value))


#@dataclass
class RxOp0(StrEnum):
    DISTINCT = auto()

    def __hash__(self):
        return hash(str(self.value))


#@dataclass
class RxOp1(StrEnum):
    DEBOUNCE = auto()
    THROTTLE = auto()

    def __hash__(self):
        return hash(str(self.value))


@dataclass
class AbstractExpr:
    pass


@dataclass
class UnaryOpExpr(AbstractExpr):
    op: UnaryOp
    expr: 'Expr'
    type: Literal['UnaryOpExpr'] = 'UnaryOpExpr'


@dataclass
class BinaryOpExpr(AbstractExpr):
    expr1: 'Expr'
    op: BinaryOp
    expr2: 'Expr'
    type: Literal['BinaryOpExpr'] = 'BinaryOpExpr'


@dataclass
class RxOp0Expr(AbstractExpr):
    op: RxOp0
    expr: 'Expr'
    type: Literal['RxOp0Expr'] = 'RxOp0Expr'
    _label: Optional[str] = None


@dataclass
class RxOp1Expr(AbstractExpr):
    op: RxOp1
    arg: float
    expr: 'Expr'
    type: Literal['RxOp1Expr'] = 'RxOp1Expr'
    _label: Optional[str] = None


@dataclass
class IfExpr(AbstractExpr):
    ifExpr: 'Expr'
    thenExpr: 'Expr'
    elseExpr: Optional['Expr'] = None
    type: Literal['IfExpr'] = 'IfExpr'


@dataclass
class When:
    ifExpr: 'Expr'
    thenExpr: 'Expr'


@dataclass
class WhenExpr(AbstractExpr):
    whens: list[When]
    elseExpr: Optional['Expr'] = None
    type: Literal['WhenExpr'] = 'WhenExpr'


@dataclass
class OnExpr(AbstractExpr):
    onExpr: 'Expr'
    thenExpr: 'Expr'
    type: Literal['OnExpr'] = 'OnExpr'
    _label: Optional[str] = None


@dataclass
class ObservableExpr(AbstractExpr):
    observableRef: str
    type: Literal['ObservableExpr'] = 'ObservableExpr'


@dataclass
class EnumValueExpr(AbstractExpr):
    enumValue: str
    type: Literal['EnumValueExpr'] = 'EnumValueExpr'


@dataclass
class ValueExpr(AbstractExpr):
    value: float
    type: Literal['ValueExpr'] = 'ValueExpr'


@dataclass
class ConvertExpr(AbstractExpr):
    expr: 'Expr'
    quantity: str
    fromUnit: str
    toUnit: str
    type: Literal['ConvertExpr'] = 'ConvertExpr'


@dataclass
class NoneExpr(AbstractExpr):
    type: Literal['NoneExpr'] = 'NoneExpr'


Expr = Annotated[(UnaryOpExpr | BinaryOpExpr | RxOp0Expr | RxOp1Expr | IfExpr | WhenExpr | OnExpr | ObservableExpr |
                  EnumValueExpr | ValueExpr | ConvertExpr | NoneExpr), Field(discriminator='type')]
