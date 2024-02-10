from dataclasses import dataclass
from datetime import datetime


@dataclass
class Identified:
    id: str


@dataclass
class Named(Identified):
    name: str


@dataclass
class Described(Identified):
    description: str


@dataclass
class Document(Identified):
    stamp: datetime
