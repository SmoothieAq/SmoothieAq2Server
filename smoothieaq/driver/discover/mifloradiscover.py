import logging
from typing import Optional

import bleak

from .btdiscover import BtDiscover
from ...model.thing import Device, DriverRef, Measure

log = logging.getLogger(__name__)


def _new_measure(id: str, name: str, quantityType: str, unit: str, precision: float) -> Measure:
    measure = Measure()
    measure.id = id
    measure.name = name
    measure.quantityType = quantityType
    measure.unit = unit
    measure.precision = precision
    return measure


class MiFloraDiscover(BtDiscover):
    id = "MiFloraDiscover"
    rx_key_battery: str = 'A'
    rx_key_temperature: str = 'B'
    rx_key_humidity: str = 'C'
    rx_key_illuminance: str = 'D'
    rx_key_moisture: str = 'E'
    rx_key_conductivity: str = 'F'
    rx_key_rssi: str = 'G'

    async def _new_bt_device(self, path: str, dev: bleak.BLEDevice, data: bleak.AdvertisementData)-> Optional[Device]:
        device = Device()
        device.name = "Flower care"
        device.description = "Xioami Mi Flower"
        device.make = device.description
        device.driver = DriverRef()
        device.driver.id  = "MiFloraDriver"
        device.driver.path = self.global_hal + ':' + path
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
        return device

    async def _subscribe(self):
        return await self.hal.subscribe(self._rx_bt, service_uuid='0000fe95-0000-1000-8000-00805f9b34fb')

