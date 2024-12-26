from typing import Type

from pydantic import RootModel
from pydantic_yaml import parse_yaml_file_as
from expression.collections.seq import Seq

from ..model import enum as aqe
from ..model import thing as aqt
from ..util.rxutil import ix
from ..device import devices

_objects: dict[any, dict[str, any]] = {}


async def _load_type(type: Type, file: str) -> None:
    all: list[type] = parse_yaml_file_as(RootModel[list[type]], f"resources/{file}.yaml").root
    print("loaded", len(all), type)
    _objects[type] = dict(ix(all).map(lambda e: (e.id, e)))


async def load() -> None:
    await _load_type(aqe.Enum, "enums")
    from .enums import load as enum_load
    enum_load()
    await _load_type(aqt.Driver, "drivers")
    await _load_type(aqt.EmitDriver, "emitdrivers")
    _objects[aqt.Device] = {}
    await devices.init()


def get[T](type: Type[T], id: str) -> T:
    return _objects[type][id]


async def put[T](type: Type[T], id: str, object: T) -> None:
    _objects[type][id] = object


async def replace[T](type: Type[T], id: str, object: T) -> None:
    _objects[type][id] = object


def get_all[T](type: Type[T]) -> Seq[T]:
    return ix(_objects[type].values())
