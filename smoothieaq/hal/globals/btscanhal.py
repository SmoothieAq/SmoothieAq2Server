from typing import Optional

import aioreactive as rx
from pydantic.v1 import UUID4

from .globalhal import GlobalHal


class BtScanHal(GlobalHal):

    async def subscribe(self, rx_subscription: rx.AsyncSubject[dict], address: Optional[str] = None, name: Optional[str] = None, service_uuid: Optional[str] = None) -> UUID4:
        pass

    async def unsubscribe(self, id: UUID4):
        pass
