from smoothieaq.model.base import *
from typing import Optional, Literal
from typing_extensions import Annotated
from pydantic import Field


@dataclass
class EnumValueBase(Named, Described):
    type: Literal['EnumValueSimple'] = 'EnumValueBase'
    deprecated: Optional[bool] = None


@dataclass
class EnumValueSimple(Named, Described):
    type: Literal['EnumValueSimple'] = 'EnumValueSimple'


@dataclass
class Unit(EnumValueBase):
    type: Literal['Unit'] = 'Unit'
    relTimes: Optional[float] = None
    relAdd: Optional[float] = None
    relUnit: Optional[str] = None
    geoArea: Optional[str] = None # enum geoArea


EnumValue = Annotated[(EnumValueSimple | Unit), Field(discriminator='type')]


@dataclass
class EnumBase[V: EnumValue](Named, Described, Document):
    type: Literal['Base'] = 'EnumBase'
    values: Optional[list[V]] = None


@dataclass
class EnumSimple(EnumBase[EnumValueSimple]):
    type: Literal['EnumSimple'] = 'EnumSimple'


@dataclass
class QuantityType(EnumBase[Unit]):
    type: Literal['QuantityType'] = 'QuantityType'


Enum = Annotated[(EnumSimple | QuantityType), Field(discriminator='type')]
