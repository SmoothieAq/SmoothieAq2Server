import importlib

from expression.collections import Seq

from ..modelobject import objectstore as os
from .emitdriver import EmitDriver
from ..model import thing as aqt


async def find_emit_driver(m_emit_driver_id: str) -> EmitDriver:
    m_emit_driver = await get_m_emit_driver(m_emit_driver_id)
    emit_driver_id = m_emit_driver.templateDevice.driver.id

    d_module = importlib.import_module("smoothieaq.emitdriver." + emit_driver_id.lower())
    d_class = getattr(d_module, emit_driver_id)
    return d_class(m_emit_driver)


async def get_m_emit_drivers() -> Seq[aqt.EmitDriver]:
    return await os.get_all(aqt.EmitDriver)


async def get_m_emit_driver(id: str) -> aqt.EmitDriver:
    return await os.get(aqt.EmitDriver, id)


async def put_m_emit_driver(m_emit_driver: aqt.EmitDriver) -> None:
    await os.put(aqt.EmitDriver, m_emit_driver.id, m_emit_driver)
