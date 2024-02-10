from dataclasses import dataclass


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
class Enum(Named, Described):
    None


@dataclass
class Enum(Named, Described):


@dataclass
class Thing(Named, Described):
    place: str
