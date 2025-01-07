import json
import logging
import os
from pathlib import Path
from typing import Type, Optional

from fastapi.encoders import jsonable_encoder
from pydantic import RootModel
from pydantic_yaml import parse_yaml_file_as
from expression.collections.seq import Seq

from smoothieaq.model import enum as aqe
from smoothieaq.model import thing as aqt
from smoothieaq.modelobject.objectpersister import ObjectPersister
from smoothieaq.modelobject.objectsqlite import ObjectSqlite
from smoothieaq.util.rxutil import ix
from smoothieaq.device import devices

log = logging.getLogger(__name__)

def _get_persister() -> Optional[ObjectPersister]:
    persister_id: str = os.environ.get("smoothieaq_persister", "none")
    match persister_id:
        case "none":
            return ObjectPersister()
        case "sqlite":
            return ObjectSqlite()
        case _:
            return ObjectPersister()

persister: Optional[ObjectPersister] = _get_persister()
_types: dict[str, Type] = {'enums': aqe.Enum, 'drivers': aqt.Driver, 'devices': aqt.Device,
                           'emitDrivers': aqt.EmitDriver, 'emitDevices': aqt.EmitDevice}
_objects: dict[any, dict[str, any]] = {}

def encode(obj) -> str:
    return json.dumps(jsonable_encoder(obj, exclude_defaults=True, exclude_none=True, exclude_unset=True))

def _decode(typ: Type, obj: str):
    return RootModel[typ].model_validate_json(obj).root

async def _load_type_from_yaml_file[T](typ: Type[T], file: str) -> Seq[T]:
    file = Path(f"resources/{file}.yaml")
    try:
        all: list[typ] = parse_yaml_file_as(RootModel[list[typ]], file).root
        log.info(f"Loaded {len(all)} {typ}")
        return ix(all)
    except FileNotFoundError:
        log.info(f"Loaded zero {typ}")
        return ix([])


async def load() -> None:
    if await persister.create_db_if_needed():
        for (typ_name, typ) in _types.items():
            objects: Seq[typ] = await _load_type_from_yaml_file(typ, typ_name)
            _objects[typ] = dict(objects.map(lambda e: (e.id, e)))
            for o in objects:
                #await persister.create(typ, o.id, RootModel(o).model_dump_json(exclude_defaults=True))
                await persister.create(typ, o.id, encode(o))
    else:
        for typ in _types.values():
            _objects[typ] = dict((await persister.get_all(typ))
                #.map(lambda s: RootModel[typ].model_validate_json(s).root).map(p)
                .map(lambda s: _decode(typ, s))
                .map(lambda e: (e.id, e)))

    from ..div.enums import load as enum_load
    await enum_load()
    await devices.init()


async def get[T](typ: Type[T], id: str) -> T:
    return _objects[typ][id]


async def put[T](typ: Type[T], id: str, object: T) -> None:
    #await persister.create(typ, id, RootModel(object).model_dump_json(exclude_defaults=True))
    await persister.create(typ, id, encode(object))
    _objects[typ][id] = object


async def replace[T](typ: Type[T], id: str, object: T) -> None:
    #await persister.update(typ, id, RootModel(object).model_dump_json(exclude_defaults=True))
    await persister.update(typ, id, encode(object))
    _objects[typ][id] = object


async def get_all[T](typ: Type[T]) -> Seq[T]:
    return ix(_objects[typ].values())
