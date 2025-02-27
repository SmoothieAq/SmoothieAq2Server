import logging
import struct
from typing import cast, Optional

import aioreactive as rx
import bleak
from expression.collections import Map
from pydantic.v1 import UUID4

from .discover import Discover
from ..driver import Driver
from ...device import devices
from ...device.devices import create_new_device
from ...hal.globals import globalhals
from ...hal.globals.btscanhal import BtScanHal
from ...model.thing import Device, DriverRef, Measure
from ...util.rxutil import AsyncBehaviorSubject

log = logging.getLogger(__name__)


def _new_measure(id: str, name: str, quantityType: str, unit: str, precision: float) -> Measure:
    measure = Measure()
    measure.id = id
    measure.name = name
    measure.quantityType = quantityType
    measure.unit = unit
    measure.precision = precision
    return measure


class MiFloraDiscover(Discover[BtScanHal]):
    id = "MiFloraDiscover"
    rx_key_battery: str = 'A'
    rx_key_temperature: str = 'B'
    rx_key_humidity: str = 'C'
    rx_key_illuminance: str = 'D'
    rx_key_moisture: str = 'E'
    rx_key_conductivity: str = 'F'
    rx_key_rssi: str = 'G'

    def __init__(self):
        super().__init__()
        self._rx_bt: AsyncBehaviorSubject[dict] = AsyncBehaviorSubject({})
        self._sub_id: Optional[UUID4] = None
        self._disposables: list[rx.AsyncDisposable] = []
        self._seen: set[str] = set()

    def init(self, path: str, hal: str, globalHal: str, params: Map[str, str]) -> 'Driver':
        log.info(f"doing discover.init({self.id}/{path})")
        self.path = path
        self.params = params
        self.is_global_hal = True
        self.global_hal = globalHal
        self.hal = cast(BtScanHal, globalhals.get_global_hal(globalHal))
        return self

    async def _new_device(self, path: str):
        try:
            device = Device()
            device.name = "Flower care"
            device.description = "Xioami Mi Flower"
            device.make = device.description
            device.driver = DriverRef()
            device.driver.id  = "MiFloraDriver"
            device.driver.path = path
            device.driver.globalHal = self.global_hal
            device.driver.params = []
            device.observables = []
            device.observables.append(_new_measure(self.rx_key_battery,'Battery', 'fraction', '%', 1.0))
            device.observables.append(_new_measure(self.rx_key_temperature,'Temperature', 'temp', '°C', 0.1))
            device.observables.append(_new_measure(self.rx_key_humidity,'Relative humidity', 'fraction', '%', 1.0))
            device.observables.append(_new_measure(self.rx_key_illuminance,'Illuminance', 'illuminance', 'lux', 1.0))
            device.observables.append(_new_measure(self.rx_key_moisture,'Soil moisture', 'fraction', '%', 1.0))
            device.observables.append(_new_measure(self.rx_key_conductivity,'Soil conductivity', 'conductivity', 'uS/cm', 1.0))
            device.observables.append(_new_measure(self.rx_key_rssi,'Link quality', 'RSSI', 'dBm', 1.0))

            id = await create_new_device(device)
            log.info(f"created new device {id} {device.name} {device.description}")
        except Exception as e:
            log.error(f"{path}", exc_info=e)

    async def _on_message(self, d: dict):
        if not d: return
        path = cast(bleak.BLEDevice, d.get('device')).address
        if path in self._seen: return
        self._seen.add(path)
        device_path = self.global_hal + ':' + path
        if device_path in devices.device_paths: return
        await self._new_device(device_path)

    async def start(self) -> None:
        await super().start()
        self._disposables.append( await self._rx_bt.subscribe_async(self._on_message))
        self._sub_id = await self.hal.subscribe(self._rx_bt, service_uuid='0000fe95-0000-1000-8000-00805f9b34fb')

    async def stop(self):
        await self.hal.unsubscribe(self._sub_id)
        await super().stop()