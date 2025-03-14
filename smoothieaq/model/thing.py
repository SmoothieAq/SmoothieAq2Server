from .base import *
from .expression import *
from .step import *
from typing import Optional, Literal, ForwardRef
from typing_extensions import Annotated
from pydantic import Field


@dataclass
class Thing(Named, Described):
    site: Optional[str] = None  # enum site
    place: Optional[str] = None  # enum place
    category: Optional[str] = None  # enum category
    imageRef: Optional[str] = None
    enablement: Optional[str] = None # enum enablement
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
class AbstractScheduleAt:
    pass


@dataclass
class AtWeekday(AbstractScheduleAt):
    type: Literal['AtWeekday'] = 'AtWeekday'
    every: Optional[list[str]] = None  # weekDay
    at: Optional[str] = None  # hh:mm


ScheduleAt = Annotated[(AtWeekday), Field(discriminator='type')]


@dataclass
class OneTime:
    atDate: Optional[str] = None # YYYY-MM-DD
    atTime: Optional[str] = None # hh:mm


@dataclass
class Plan:
    everyDays: Optional[int] = None
    atWeekDays: Optional[list[str]] = None # weekDay
    atTime: Optional[str] = None  # hh:mm
    relativeToLast: Optional[bool] = None
    warningFraction: Optional[float] = None # default 0.1
    skipIfLastCloseFraction: Optional[float] = None # default 0.33
    delayFraction: Optional[float] = None # default 0.15


@dataclass
class Schedule(Identified):
    at: Optional[AtWeekday] = None
    program: Optional[Program] = None
    disabled: Optional[bool] = None
    pauseExpr: Optional[Expr] = None


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
    hal: Optional[str] = None
    globalHal: Optional[str] = None
    params: list[Param] = None


@dataclass
class AbstractObservable(Thing):
    driver: Optional[DriverRef] = None
    operations: Optional[list[str]] = None  # operation
    expr: Optional[Expr] = None
    pauseExpr: Optional[Expr] = None


@dataclass
class ValueObservable(AbstractObservable):
    quantityType: Optional[str] = None # QuantityTpe
    unit: Optional[str] = None # Unit of QuantityType
    require: Optional[ValueRequire] = None
    precision: Optional[float] = None
    setExpr: Optional[Expr] = None
    controller: Optional[bool] = None


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


@dataclass
class Action(AbstractObservable):
    type: Literal['Action'] = 'Action'
    steps: Optional[list[Step]] = None
    runAsync: Optional[bool] = None
    timeout: Optional[float] = None


@dataclass
class Chore(AbstractObservable):
    type: Literal['Chore'] = 'Chore'
    plan: Optional[Plan] = None
    oneTime: Optional[OneTime] = None
    steps: Optional[list[Step]] = None
    autoDone: Optional[bool] = None
    timeout: Optional[float] = None

Observable = Annotated[(Measure | Amount | State | Event | Action | Chore), Field(discriminator='type')]


@dataclass
class Device(Thing):
    make: Optional[str] = None
    type: Optional[str] = None  # enum deviceType
    driver: Optional[DriverRef] = None
    pauseExpr: Optional[Expr] = None
    operations: Optional[list[str]] = None  # operations
    observables: Optional[list[Observable]] = None
    schedules: Optional[list[Schedule]] = None


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
    type: Optional[str] = None # enum type
    site: Optional[str] = None  # enum site
    place: Optional[str] = None  # enum place
    category: Optional[str] = None  # enum category


@dataclass
class EmitDevice(Named, Described):
    type: Optional[str] = None  # enum emitDeviceType
    driver: Optional[DriverRef] = None
    operations: Optional[list[str]] = None  # enum emitOperation
    enablement: Optional[str] = None # enum enablement
    include: Optional[list[EmitDeviceFilter]] = None
    exclude: Optional[list[EmitDeviceFilter]] = None
    bufferNo: Optional[int] = None
    bufferTime: Optional[float] = None


@dataclass
class EmitDriver(Named, Described):
    paramDescriptions: Optional[list[ParamDescription]] = None
    templateDevice: Optional[EmitDevice] = None



