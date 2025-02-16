import importlib

from smoothieaq.hal.hal import Hal


_d_classes = {}

def get_hal(hal_name: str) -> Hal:
    try:
        d_class = _d_classes[hal_name]
    except KeyError:
        d_module = importlib.import_module("smoothieaq.hal." + hal_name.lower())
        d_class = getattr(d_module, hal_name)
        _d_classes[hal_name] = d_class
    return d_class()
