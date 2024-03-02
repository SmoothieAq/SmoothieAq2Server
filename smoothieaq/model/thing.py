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
class Condition(Described):
    condition: Optional[Expr] = None


@dataclass
class ValueRequire:
    warningAbove: Optional[float] = None
    warningBelow: Optional[float] = None
    alarmAbove: Optional[float] = None
    alarmBelow: Optional[float] = None
    warningConditions: Optional[list[Condition]] = None
    alarmConditions: Optional[list[Condition]] = None


@dataclass
class EnumRequire:
    alarmIfIn: Optional[list[str]] = None
    alarmIfNotIn: Optional[list[str]] = None
    warningConditions: Optional[list[Condition]] = None
    alarmConditions: Optional[list[Condition]] = None


@dataclass
class DriverRef:
    id: Optional[str] = None
    path: Optional[str] = None
    params: list[Param] = None


@dataclass
class AbstractObservable(Thing):
    driver: Optional[DriverRef] = None
    operations: Optional[list[str]] = None  # operations
    expr: Optional[Expr] = None


@dataclass
class ValueObservable(AbstractObservable):
    quantityType: Optional[str] = None
    require: Optional[ValueRequire] = None
    precision: Optional[float] = None
    setExpr: Optional[Expr] = None


@dataclass
class MeasureEmitControl:
    decimals: Optional[float] = None
    supressSameLimit: Optional[float] = None
    # outlierSuppress: Optional[bool] = None
    atMostEverySecond: Optional[float] = None
    # atLeastEveryMinute: Optional[float] = None


@dataclass
class Measure(ValueObservable):
    type: Literal['Measure'] = 'Measure'
    emitControl: Optional[MeasureEmitControl] = None


@dataclass
class Amount(ValueObservable):
    type: Literal['Amount'] = 'Amount'
    resetExpr: Optional[Expr] = None
    addExpr: Optional[Expr] = None


@dataclass
class State(AbstractObservable):
    type: Literal['State'] = 'State'
    enumType: Optional[str] = None
    setExpr: Optional[Expr] = None
    require: Optional[EnumRequire] = None


@dataclass
class EventEmitControl:
    # afterSeconds: Optional[float] = None
    debounceValue: Optional[float] = None


@dataclass
class Event(AbstractObservable):
    type: Literal['Event'] = 'Event'
    enumType: Optional[str] = None
    quantityType: Optional[str] = None
    emitControl: Optional[EventEmitControl] = None


Observable = Annotated[(Measure | Amount | State | Event), Field(discriminator='type')]


@dataclass
class Device(Thing):
    make: Optional[str] = None
    type: Optional[str] = None  # enum deviceType
    driver: Optional[DriverRef] = None
    operations: Optional[list[str]] = None  # operations
    observables: Optional[list[Observable]] = None


@dataclass
class Driver(Named, Described):
    canDiscover: Optional[bool] = None
    canMultiInstance: Optional[bool] = None
    canSingleObservable: Optional[bool] = None
    paramDescriptions: Optional[list[ParamDescription]] = None
    templateDevice: Optional[Device] = None
    basedOnDriver: Optional[str] = None


@dataclass
class EmitDeviceFilter:
    id: Optional[str] = None
    statusObservable: Optional[bool] = None
    site: Optional[str] = None  # enum site
    place: Optional[str] = None  # enum place
    category: Optional[str] = None  # enum category


@dataclass
class EmitDevice(Named, Described):
    type: Optional[str] = None  # enum emitDeviceType
    driver: Optional[DriverRef] = None
    operations: Optional[list[str]] = None  # enum emitOperation
    enabled: Optional[bool] = None
    include: Optional[list[EmitDeviceFilter]] = None
    exclude: Optional[list[EmitDeviceFilter]] = None
    bufferNo: Optional[int] = None
    bufferTime: Optional[float] = None


@dataclass
class EmitDriver(Named, Described):
    paramDescriptions: Optional[list[ParamDescription]] = None
    templateDevice: Optional[EmitDevice] = None



