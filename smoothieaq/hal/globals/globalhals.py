import importlib

from expression.collections import Map, Block

from .globalhal import GlobalHal
from ...modelobject import objectstore as os
from ...model import globals as aqg


_d_classes = {}

def get_hal(hal_name: str) -> GlobalHal:
    try:
        d_class = _d_classes[hal_name]
    except KeyError:
        d_module = importlib.import_module("smoothieaq.hal.globals." + hal_name.lower())
        d_class = getattr(d_module, hal_name)
        _d_classes[hal_name] = d_class
    return d_class()

_globalHals: dict[str, GlobalHal] = {}
_globals: aqg.Globals

async def init():
    global _globals
    _globals = await os.get(aqg.Globals, 'globals')


def get_global_hal(instance_name: str) -> GlobalHal:
    try:
        return _globalHals[instance_name]
    except KeyError:
        for gh in _globals.globalHals:
            if gh.id == instance_name and not gh.disabled == True:
                path = gh.driverRef.path or gh.id
                params = Map.of_block(Block(gh.driverRef.params or []).map(lambda p: (p.key, p.value)))
                hal = get_hal(gh.driverRef.globalHal)
                hal.init(path, params)
                _globalHals[gh.id] = hal
                return hal
        raise KeyError