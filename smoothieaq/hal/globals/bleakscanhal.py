import logging
import uuid
from itertools import zip_longest
from typing import Optional, Callable, Awaitable

import aioreactive as rx
import bleak
from expression.collections import Map
from pydantic import UUID4

from .btscanhal import BtScanHal
from .mqtthal import MqttHal

log = logging.getLogger(__name__)


class BleakScanHal(BtScanHal):

    def __init__(self) -> None:
        super().__init__()
        self.scanner: Optional[bleak.BleakScanner] = None
        self.subscriptions: dict[UUID4, ((str, str, str), rx.AsyncSubject[dict])] = {}
        self.addresses: set[str] = set()
        self.names: set[str] = set()
        self.service_ids: set[str] = set()

    async def on_advertised(self, device: bleak.BLEDevice, data: bleak.AdvertisementData):
        a_address = device.address
        a_name = device.name
        a_service_uuids = data.service_uuids
        def anyin(anyl: list[str], ins: set[str]) -> bool:
            for e in anyl:
                if e in ins: return True
            return False
        if not (a_address in self.addresses or (a_name and a_name in self.names) or (a_service_uuids and anyin(a_service_uuids, self.service_ids))):
            return

        for ((address, name, service_uuid), rx_subscription) in list(self.subscriptions.values()):
            if ((address == None or address == a_address) and
                (name == None or name == a_name) and
                (service_uuid == None or service_uuid in a_service_uuids)
            ):
                d = {'device': device, 'data': data}
                await rx_subscription.asend(d)

    async def global_start(self):
        try:
            self.scanner = bleak.BleakScanner(detection_callback=self.on_advertised, scanning_mode=(self.params.get('scanning_mode') or 'passive'))
            await self.scanner.start()
        except Exception as e:
            log.error("Could not start scanning", exc_info=e)
            # todo, some status observable...

    async def global_stop(self):
        await self.scanner.stop()

    async def subscribe(self, rx_subscription: rx.AsyncSubject[dict], address: Optional[str] = None, name: Optional[str] = None, service_uuid: Optional[str] = None) -> UUID4:
        id = uuid.uuid4()
        log.info(f"subscribe {address} {name} {service_uuid}")
        if address: self.addresses.add(address)
        if name: self.names.add(name)
        if service_uuid: self.service_ids.add(service_uuid)
        self.subscriptions[id] = ((address, name, service_uuid), rx_subscription)
        return id

    async def unsubscribe(self, id: UUID4):
        del self.subscriptions[id]

