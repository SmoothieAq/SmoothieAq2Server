import importlib
from copy import deepcopy
from typing import Optional

from expression.collections import Seq

from ..div import objectstore as os
from .driver import Driver
from ..model import thing as aqt
from ..util.dataclassutil import overwrite


def get_driver(driver_id: str) -> Driver:
    d_module = importlib.import_module("smoothieaq.driver." + driver_id.lower())
    d_class = getattr(d_module, driver_id)
    return d_class()


def get_m_drivers() -> Seq[aqt.Driver]:
    return os.get_all(aqt.Driver)


def get_m_driver(id: str) -> aqt.Driver:
    m_driver = os.get(aqt.Driver, id)
    if m_driver.basedOnDriver:
        m_based = get_m_driver(m_driver.basedOnDriver)
        m_driver = overwrite(m_based, m_driver)
    return m_driver


def put_m_driver(m_driver: aqt.Driver) -> None:
    os.put(aqt.Driver, m_driver.id, m_driver)


def create_m_device(m_driver: aqt.Driver, driver_info: Optional[aqt.DriverRef] = None) -> aqt.Device:
    #print(m_driver)
    m_device = deepcopy(m_driver.templateDevice)
    if driver_info:
        if driver_info.path:
            m_device.driver.path = driver_info.path
        if driver_info.params:
            overwrite(m_device.driver.params, driver_info.params)
    return m_device


def create_m_observable(m_driver: aqt.Driver, driver_info: Optional[aqt.DriverRef] = None) -> aqt.Observable:
    m_observable = deepcopy(m_driver.templateDevice.observables[0])
    m_observable.driver = deepcopy(m_driver.templateDevice.driver)
    if driver_info:
        if driver_info.path:
            m_observable.driver.path = driver_info.path
        if driver_info.params:
            overwrite(m_observable.driver.params, driver_info.params)
    return m_observable

