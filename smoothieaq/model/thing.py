from smoothieaq.model.base import *
from smoothieaq.model.expression import *
from typing import Optional, Literal, ForwardRef
from typing_extensions import Annotated
from pydantic import Field


@dataclass
class Thing(Named, Described):
    site: Optional[str] = None  # enum site
    place: Optional[str] = None  # enum place
    category: Optional[str] = None  # enum category
    imageRef: Optional[str] = None
    enabled: Optional[bool] = None
    pausedIf: Optional[Expr] = None


@dataclass
class Param:
    key: str
    value: str


@dataclass
class ParamDescription(Described):
    key: Optional[str] = None
    defaultValue: Optional[str] = None


@dataclass
class ValueRequire:
    warningNoAbove: Optional[float] = None
    warningNotBelow: Optional[float] = None
    isAbove: Optional[float] = None
    isBelow: Optional[float] = None
    isCondition: Optional[Expr] = None


@dataclass
class EnumRequire:
    isNot: Optional[list[str]] = None
    isOnly: Optional[list[str]] = None
    isCondition: Optional[Expr] = None


@dataclass
class DriverRef:
    id: str
    path: Optional[str] = None
    params: list[Param] = None


@dataclass
class AbstractObservable(Thing):
    driver: Optional[DriverRef] = None
    operations: Optional[list[str]] = None  # operations


@dataclass
class ValueObservable(AbstractObservable):
    quantityType: Optional[str] = None
    expr: Optional[Expr] = None
    require: Optional[ValueRequire] = None
    precision: Optional[float] = None


@dataclass
class MeasureEmitControl:
    decimals: Optional[float] = None
    supressSameLimit: Optional[float] = None
    outlierSuppress: Optional[bool] = None
    atMostEverySecond: Optional[float] = None
    atLeastEveryMinute: Optional[float] = None


@dataclass
class Measure(ValueObservable):
    type: Literal['Measure'] = 'Measure'
    emitControl: Optional[MeasureEmitControl] = None


@dataclass
class Amount(ValueObservable):
    type: Literal['Amount'] = 'Amount'
    initialValue: Optional[Expr] = None
    setExpr: Optional[Expr] = None


@dataclass
class State(AbstractObservable):
    type: Literal['State'] = 'State'
    enumType: Optional[str] = None
    expr: Optional[Expr] = None
    setExpr: Optional[Expr] = None
    require: Optional[EnumRequire] = None
    resetValue: Optional[Expr] = None


@dataclass
class EventEmitControl:
    afterSeconds: Optional[float] = None
    debounceValue: Optional[float] = None


@dataclass
class Event(AbstractObservable):
    type: Literal['State'] = 'State'
    enumType: Optional[str] = None
    quantityType: Optional[str] = None
    expr: Optional[Expr] = None
    emitControl: Optional[EventEmitControl] = None


Observable = Annotated[(Measure | Amount | State | Event), Field(discriminator='type')]


@dataclass
class Device(Thing):
    make: Optional[str] = None
    type: Optional[str] = None  # enum deviceType
    driver: Optional[DriverRef] = None
    observables: Optional[list[Observable]] = None


@dataclass
class Driver(Named, Described):
    canDiscover: Optional[bool] = None
    canMultiInstance: Optional[bool] = None
    canSingleObservable: Optional[bool] = None
    paramDescriptions: Optional[list[ParamDescription]] = None
    templateDevice: Optional[Device] = None
