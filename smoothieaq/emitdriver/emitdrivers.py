import importlib

from expression.collections import Seq

from ..div import objectstore as os
from .emitdriver import EmitDriver
from ..model import thing as aqt


def find_emit_driver(m_emit_driver_id: str) -> EmitDriver:
    m_emit_driver = get_m_emit_driver(m_emit_driver_id)
    emit_driver_id = m_emit_driver.templateDevice.driver.id

    d_module = importlib.import_module("smoothieaq.emitdriver." + emit_driver_id.lower())
    d_class = getattr(d_module, emit_driver_id)
    return d_class(m_emit_driver)


def get_m_emit_drivers() -> Seq[aqt.EmitDriver]:
    return os.get_all(aqt.EmitDriver)


def get_m_emit_driver(id: str) -> aqt.EmitDriver:
    return os.get(aqt.EmitDriver, id)


def put_m_emit_driver(m_emit_driver: aqt.EmitDriver) -> None:
    os.put(aqt.EmitDriver, m_emit_driver.id, m_emit_driver)
