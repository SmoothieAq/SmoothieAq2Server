import logging
import struct
from asyncio import sleep
from typing import cast, Optional

import aioreactive as rx
import bleak
from expression.collections import Map, Block
from pydantic.v1 import UUID4

from smoothieaq.div.emit import RawEmit
from .discover.mifloradiscover import MiFloraDiscover
from .driver import Status
from .driver import Driver
from ..hal.globals import globalhals
from ..hal.globals.btscanhal import BtScanHal
from ..hal.globals.mqtthal import MqttHal
from ..util.rxutil import AsyncBehaviorSubject, do_later, trace, publish

log = logging.getLogger(__name__)

rx_bridge_availability: Optional[AsyncBehaviorSubject[dict]] = AsyncBehaviorSubject({})
_bridge: bool = False

_sensors = {
    "battery": MiFloraDiscover.rx_key_battery,
    "temperature": MiFloraDiscover.rx_key_temperature,
    "humidity": MiFloraDiscover.rx_key_humidity,
    "illuminance": MiFloraDiscover.rx_key_illuminance,
    "moisture": MiFloraDiscover.rx_key_moisture,
    "conductivity": MiFloraDiscover.rx_key_conductivity
}

class MiFloraDriver(Driver[BtScanHal]):
    id = "MiFloraDriver"

    def __init__(self):
        super().__init__()
        self._rx_bt: AsyncBehaviorSubject[dict] = AsyncBehaviorSubject({})
        self._sub_id: Optional[UUID4] = None
        self._disposables: list[rx.AsyncDisposable] = []

    def _set_subjects(self) -> dict[str, rx.AsyncSubject]:
        return { id: rx.AsyncSubject[RawEmit]() for id in [
            MiFloraDiscover.rx_key_battery,
            MiFloraDiscover.rx_key_temperature,
            MiFloraDiscover.rx_key_humidity,
            MiFloraDiscover.rx_key_illuminance,
            MiFloraDiscover.rx_key_moisture,
            MiFloraDiscover.rx_key_conductivity
        ]}

    def _init(self):
        super()._init()

    async def _on_message(self, d: dict):
        if not d: return {}
        data = cast(bleak.AdvertisementData, d.get('data'))
        if not data: return {}
        values = decode(data.service_data)
        for (name, id) in _sensors.items():
            value = values.get(name)
            if not value is None:
                await self._rx_observers[id].asend(RawEmit(value))

    async def start(self) -> None:
        await super().start()
        self._disposables.append(await self._rx_bt.subscribe_async(self._on_message))
        self._sub_id = await self.hal.subscribe(self._rx_bt, address=self.path.split(":")[1])

    async def stop(self) -> None:
        await self.hal.unsubscribe(self._sub_id)
        for disposable in self._disposables:
            await disposable.dispose_async()
        await super().stop()


def decode(service_data: dict[str, bytes]) -> dict[str, float]:
    midata = service_data.get('0000fe95-0000-1000-8000-00805f9b34fb')
    if not midata or len(midata) < 15: return {}
    (mitype,) = struct.unpack("<h", midata[12:14])
    unpac = xiaomi_dataobject_dict.get(mitype)
    if not unpac:
        log.warning(f"Unknown Mi Flora message type {mitype}")
        return {}
    return unpac(midata[15:])


# The following is largely copied from: https://github.com/custom-components/ble_monitor/blob/master/custom_components/ble_monitor/ble_parser/xiaomi.py

TH_STRUCT = struct.Struct("<hH")
H_STRUCT = struct.Struct("<H")
T_STRUCT = struct.Struct("<h")
CND_STRUCT = struct.Struct("<H")
ILL_STRUCT = struct.Struct("<I")

def obj1004(xobj):
    """Temperature"""
    if len(xobj) == 2:
        (temp,) = T_STRUCT.unpack(xobj)
        return {"temperature": temp / 10.0}
    else:
        return {}


def obj1006(xobj):
    """Humidity"""
    if len(xobj) == 2:
        (humi,) = H_STRUCT.unpack(xobj)
        return {"humidity": humi / 10.0}
    else:
        return {}


def obj1007(xobj):
    """Illuminance"""
    if len(xobj) == 3:
        (illum,) = ILL_STRUCT.unpack(xobj + b'\x00')
        return {"illuminance": illum * 1.0}
    else:
        return {}


def obj1008(xobj):
    """Moisture"""
    return {"moisture": xobj[0] * 1.0}


def obj1009(xobj):
    """Conductivity"""
    if len(xobj) == 2:
        (cond,) = CND_STRUCT.unpack(xobj)
        return {"conductivity": cond * 1.0}
    else:
        return {}


def obj100a(xobj):
    """Battery"""
    batt = xobj[0]
    return {"battery": batt * 1.0}


def obj100d(xobj):
    """Temperature and humidity"""
    if len(xobj) == 4:
        (temp, humi) = TH_STRUCT.unpack(xobj)
        return {"temperature": temp / 10.0, "humidity": humi / 10.0}
    else:
        return {}

xiaomi_dataobject_dict = {
    0x1004: obj1004,
    0x1006: obj1006,
    0x1007: obj1007,
    0x1008: obj1008,
    0x1009: obj1009,
    0x100A: obj100a,
    0x100D: obj100d,
}

