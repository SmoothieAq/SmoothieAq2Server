from .thing import *


@dataclass
class GlobalHal(Described):
    disabled: Optional[bool] = None
    type: Optional[str] = None
    driverRef: Optional[DriverRef] = None


@dataclass
class Globals(Identified):
    globalHals: Optional[list[GlobalHal]] = None


