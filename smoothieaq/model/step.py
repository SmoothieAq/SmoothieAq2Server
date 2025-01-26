from dataclasses import dataclass
from typing import Optional, Literal
from typing_extensions import Annotated
from pydantic import Field

from .expression import Expr
from .base import Described

@dataclass
class Transition:
    type: Optional[str] = None  # transitionType
    length: Optional[str] = None  # hours:mins:secs.msecs
    arg: Optional[float] = None  # depends on type, blink: blink interval, s: steepness
    step: Optional[float] = None

@dataclass
class ProgramValue:
    id: Optional[str] = None  # id of observable
    value: Optional[float] = None
    enumValue: Optional[str] = None

@dataclass
class Program:
    length: Optional[str] = None  # hours:mins:secs.msecs
    values: Optional[list[ProgramValue]] = None
    transition: Optional[Transition] = None
    inTransition: Optional[list[Transition]] = None
    outTransition: Optional[Transition] = None


@dataclass
class AbstractStep(Described):
    pass

@dataclass
class ActionStep(AbstractStep):
    actionRef: str = ""
    type: Literal['ActionStep'] = 'ActionStep'

@dataclass
class EnableStep(AbstractStep):
    observableRef: str = ""
    type: Literal['EnableStep'] = 'EnableStep'

@dataclass
class DisableStep(AbstractStep):
    observableRef: str = ""
    type: Literal['DisableStep'] = 'DisableStep'

@dataclass
class PauseStep(AbstractStep):
    observableRef: str = ""
    type: Literal['PauseStep'] = 'PauseStep'

@dataclass
class UnpauseStep(AbstractStep):
    observableRef: str = ""
    type: Literal['UnpauseStep'] = 'UnpauseStep'

@dataclass
class PollStep(AbstractStep):
    observableRef: str = ""
    type: Literal['PollStep'] = 'PollStep'

@dataclass
class ResetValueStep(AbstractStep):
    observableRef: str = ""
    type: Literal['ResetValueStep'] = 'ResetValueStep'

@dataclass
class SetValueStep(AbstractStep):
    observableRef: str = ""
    expr: Optional['Expr'] = None
    type: Literal['SetValueStep'] = 'SetValueStep'

@dataclass
class AddValueStep(AbstractStep):
    observableRef: str = ""
    expr: Optional['Expr'] = None
    type: Literal['AddValueStep'] = 'AddValueStep'

@dataclass
class FireStep(AbstractStep):
    observableRef: str = ""
    expr: Optional['Expr'] = None
    type: Literal['FireStep'] = 'FireStep'

@dataclass
class AssertStep(AbstractStep):
    condition: Optional['Expr'] = None
    type: Literal['AssertStep'] = 'AssertStep'

@dataclass
class WaitStep(AbstractStep):
    timeToWait: Optional[float] = None
    type: Literal['WaitStep'] = 'WaitStep'

@dataclass
class WaitUntilStep(AbstractStep):
    condition: Optional['Expr'] = None
    maxWait: Optional[float] = None
    type: Literal['WaitUntilStep'] = 'WaitUntilStep'

@dataclass
class StopIfStep(AbstractStep):
    condition: Optional['Expr'] = None
    type: Literal['StopIfStep'] = 'StopIfStep'

@dataclass
class ListStep(AbstractStep):
    steps: Optional[list['Step']] = None
    type: Literal['ListStep'] = 'ListStep'

@dataclass
class ParallelStep(AbstractStep):
    steps: Optional[list['Step']] = None
    type: Literal['ParallelStep'] = 'ParallelStep'

@dataclass
class ProgramStep(AbstractStep):
    program: Optional[Program] = None
    type: Literal['ProgramStep'] = 'ProgramStep'

@dataclass
class InputStep(AbstractStep):
    prompt: Optional[str] = None
    autoAcceptExpr: Optional['Expr'] = None
    type: Literal['InputStep'] = 'InputStep'

@dataclass
class DoneStep(AbstractStep):
    type: Literal['DoneStep'] = 'DoneStep'


Step = Annotated[(ActionStep | EnableStep | DisableStep | PauseStep | UnpauseStep | PollStep | ResetValueStep | SetValueStep |
                  AddValueStep | FireStep | AssertStep | WaitStep | WaitUntilStep | StopIfStep | ListStep | ParallelStep |
                  ProgramStep | InputStep),
                Field(discriminator='type')]
