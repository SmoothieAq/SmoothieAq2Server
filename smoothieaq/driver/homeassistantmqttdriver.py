import logging
from typing import cast, Optional

import aioreactive as rx
from expression.collections import Map, Block

from smoothieaq.div.emit import RawEmit
from .driver import Status
from .driver import Driver
from ..hal.globals import globalhals
from ..hal.globals.mqtthal import MqttHal
from ..util.rxutil import AsyncBehaviorSubject

log = logging.getLogger(__name__)


class HomeAssistantMqttDriver(Driver[MqttHal]):
    id = "HomeAssistantMqttDriver"

    def __init__(self):
        super().__init__()
        self._rx_mqtt: AsyncBehaviorSubject[dict] = AsyncBehaviorSubject({})

    def init(self, path: str, hal: str, globalHal: str, params: Map[str, str]) -> 'Driver':
        log.info(f"doing driver.init({self.id}/{path})")
        self.path = path
        self.params = params
        self.is_global_hal = True
        self.hal = cast(MqttHal, globalhals.get_global_hal(globalHal))
        self.rx_observables = {}
        for k in self.params.keys():
            def attr(d: dict) -> Optional[RawEmit]:
                try:
                    return RawEmit(d[k])
                except Exception:
                    return None

            obs = rx.pipe(self._rx_mqtt,
                    rx.map(attr),
                    rx.filter(lambda re: re is not None)
            )
            self.rx_observables[params[k]] = obs
        return self

    async def _on_message(self, json: dict):
       pass

    async def start(self) -> None:
        await super().start()
        await self.hal.subscribe(self.path, self._rx_mqtt)
        await self.set_status(Status.RUNNING)

    async def stop(self) -> None:
        await self.hal.unsubscribe(self.path)
        await super().stop()