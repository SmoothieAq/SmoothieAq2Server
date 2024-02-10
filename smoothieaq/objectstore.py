from pydantic import RootModel
from pydantic_yaml import parse_yaml_file_as
from typing import Type

from .model import enum as aqe
from .model import thing as aqt

_objects: dict[any, dict[str, any]] = {}


def _load_type(type: Type, file: str) -> None:
    all: list[type] = parse_yaml_file_as(RootModel[list[type]], f"resources/{file}.yaml").root
    print("loaded", len(all), type)
    _objects[type] = dict(map(lambda e: (e.id, e), all))


def load() -> None:
    _load_type(aqe.Enum, "enums")
    _load_type(aqt.Driver, "drivers")

    # enums: list[aqe.Enum] = parse_yaml_file_as(RootModel[list[aqe.Enum]], "resources/enums.yaml").root
    # objects[aqe.Enum] = dict(map(lambda e: (e.id, e), enums))
    #
    # drivers: list[aqt.Driver] = parse_yaml_file_as(RootModel[list[aqe.Enum]], "resources/drivers.yaml").root
    # objects[aqt.Driver] = dict(map(lambda e: (e.id, e), drivers))


def get[T](type: Type[T], id: str) -> T:
    return _objects[type][id]


def get_all[T](type: Type[T]) -> list[T]:
    return list(_objects[type].values())
