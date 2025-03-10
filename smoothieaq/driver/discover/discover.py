import logging
from typing import Optional

from ...driver.driver import Driver
from ...hal.hal import Hal
from ...model.thing import Device

log = logging.getLogger(__name__)


class Discover[H: Hal](Driver[H]):

    async def _new_device(self, path: str, d: dict) -> Optional[Device]:
        pass

    async def new_device(self, path: str, d: dict) -> str:
        try:
            device = await self._new_device(path, d)
            if device is None:
                return "ignored"
            from ...device.devices import create_new_device
            id = await create_new_device(device)
            log.info(f"created new device {id} {device.name} {device.description}")
            return id
        except Exception as e:
            log.error(f"{path}", exc_info=e)
            return "failed"

