import importlib

from smoothieaq.div import objectstore as os
from smoothieaq.driver.driver import Driver
from smoothieaq.model import thing as aqt


def find_driver(m_driver_id: str) -> Driver:
    m_driver = get_m_driver(m_driver_id)
    driver_id = m_driver.templateDevice.driver.id

    d_module = importlib.import_module("smoothieaq.driver." + driver_id.lower())
    d_class = getattr(d_module, driver_id)
    return d_class(m_driver)


def get_m_drivers() -> list[aqt.Driver]:
    return os.get_all(aqt.Driver)


def get_m_driver(id: str) -> aqt.Driver:
    return os.get(aqt.Driver, id)


def put_m_driver(m_driver: aqt.Driver) -> None:
    os.put(aqt.Driver, m_driver.id, m_driver)
