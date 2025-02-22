import importlib

from .discover import Discover


def get_discover(driver_id: str) -> Discover:
    d_module = importlib.import_module("smoothieaq.driver.discover." + driver_id.lower())
    d_class = getattr(d_module, driver_id)
    return d_class()
