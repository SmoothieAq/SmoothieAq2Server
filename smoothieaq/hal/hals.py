import importlib

from smoothieaq.hal.hal import Hal


def get_hal(hal_name: str) -> Hal:
    d_module = importlib.import_module("smoothieaq.hal." + hal_name.lower())
    d_class = getattr(d_module, hal_name)
    return d_class()
