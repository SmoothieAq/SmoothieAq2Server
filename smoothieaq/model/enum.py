from dataclasses import dataclass
from base import *


@dataclass
class EnumValue(Named, Described):
    name: str


@dataclass
class Enum(Document, Named, Described):
    values: list[EnumValue]
