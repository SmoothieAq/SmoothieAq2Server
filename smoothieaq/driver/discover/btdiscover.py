import logging
from typing import cast, Optional

import aioreactive as rx
import bleak
from expression.collections import Map
from pydantic.v1 import UUID4

from .discover import Discover
from ..driver import Driver
from ...device import devices
from ...hal.globals import globalhals
from ...hal.globals.btscanhal import BtScanHal
from ...model.thing import Device
from ...util.rxutil import AsyncBehaviorSubject

log = logging.getLogger(__name__)


class BtDiscover(Discover[BtScanHal]):
    id = "BtDiscover"

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

    async def _new_bt_device(self, path: str, dev: bleak.BLEDevice, data: bleak.AdvertisementData)-> Optional[Device]:
        pass

    async def _new_device(self, path: str, d: dict)-> Optional[Device]:
        return await self._new_bt_device(path, cast(bleak.BLEDevice, d.get('device')), cast(bleak.AdvertisementData, d.get('data')))

    async def _on_message(self, d: dict):
        if not d: return
        path = cast(bleak.BLEDevice, d.get('device')).address
        if path in self._seen: return
        self._seen.add(path)
        device_path = self.global_hal + ':' + path
        if device_path in devices.device_paths: return
        await self.new_device(path, d)

    async def _subscribe(self) -> UUID4:
        pass

    async def start(self) -> None:
        await super().start()
        self._disposables.append( await self._rx_bt.subscribe_async(self._on_message))
        self._sub_id = await self._subscribe()

    async def stop(self):
        await self.hal.unsubscribe(self._sub_id)
        await super().stop()