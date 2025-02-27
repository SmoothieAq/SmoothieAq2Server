import logging
from asyncio import sleep
from typing import cast, Optional

import aioreactive as rx
from expression.collections import Map, Block

from smoothieaq.div.emit import RawEmit
from .driver import Status
from .driver import Driver
from ..hal.globals import globalhals
from ..hal.globals.mqtthal import MqttHal
from ..util.rxutil import AsyncBehaviorSubject, do_later, trace, publish

log = logging.getLogger(__name__)

rx_bridge_availability: Optional[AsyncBehaviorSubject[dict]] = AsyncBehaviorSubject({})
_bridge: bool = False


class HomeAssistantMqttDriver(Driver[MqttHal]):
    id = "HomeAssistantMqttDriver"

    def __init__(self):
        super().__init__()
        self._rx_mqtt: AsyncBehaviorSubject[dict] = AsyncBehaviorSubject({})
        self._params: dict[str,(str,str,str,list[str],str)] = {}
        self.rx_availability: AsyncBehaviorSubject[dict] = AsyncBehaviorSubject[dict]({})

    def init(self, path: str, hal: str, globalHal: str, params: Map[str, str]) -> 'Driver':
        log.info(f"doing driver.init({self.id}/{path})")
        self.path = path
        self.params = params
        self.is_global_hal = True
        self.hal = cast(MqttHal, globalhals.get_global_hal(globalHal))
        self.rx_observables = {}
        for k in params.keys():
            vals = params[k].split(':')
            obs_id = vals[0]
            type = vals[1]
            op = vals[2]
            bools = vals[3].split('/') if type == 'B' else []
            cmd = vals[4]
            self._params[obs_id] = (k, type, op, bools, cmd)

            def attr(obs_id: str):
                def _attr(d: dict) -> Optional[RawEmit]:
                    if not d: return None
                    (name, type, op, bools, cmd) = self._params[obs_id]
                    try:
                        val = d.get(name)
                        if val is None:
                            return None
                        if type == 'F':
                            return RawEmit(float(val))
                        elif type == 'B':
                            if str(val) == bools[0]:
                                return RawEmit(enumValue='true')
                            else:
                                return RawEmit(enumValue='false')
                        else:
                            return RawEmit(enumValue=str(val))
                    except Exception as e:
                        log.debug(f"{self.id}/{path}) {name}", exc_info=e)
                        return None
                return _attr

            obs = rx.pipe(self._rx_mqtt,
                    rx.map(attr(obs_id)),
                    rx.filter(lambda re: not re is None)
            )
            if not type == 'E':
                obs = rx.pipe(obs, rx.distinct_until_changed)
            self.rx_observables[obs_id] = obs

            def status(t: tuple[tuple[RawEmit, dict], dict]) -> RawEmit:
                try:
                    ((stat, avail1), avail2) = t
                    if avail1 and not avail1.get('state') == 'online':
                        return RawEmit(enumValue=Status.IN_ERROR, note="Bridge not online")
                    if avail2 and not avail2.get('state') == 'online':
                        return RawEmit(enumValue=Status.IN_ERROR, note="Device not online")
                    return stat
                except Exception as e:
                    log.error(exc_info=e)

            self.rx_status_observable = rx.pipe(self.rx_status_observable,
                             rx.combine_latest(rx_bridge_availability),
                             rx.combine_latest(self.rx_availability),
                             rx.map(status),
                             rx.distinct_until_changed,
                             )
        return self

    async def set(self, rx_key: str, emit: RawEmit) -> None:
        log.debug(f"doing driver.set({self.id}/{self.path}, {rx_key}, {emit})")
        (name, type, op, bools, cmd) = self._params[rx_key]
        if type == 'F':
            val = str(emit.value)
        elif type == 'B':
            val = bools[0 if emit.enumValue == 'true' else 1]
        else:
            val = emit.enumValue
        await self.hal.publish(cmd, val)

    async def start(self) -> None:
        await super().start()
        await self.hal.subscribe(self.path, self._rx_mqtt)
        await self.hal.subscribe(self.path + "/availability", self.rx_availability)
        await self.set_status(Status.RUNNING)
        global _bridge
        if not _bridge:
            await self.hal.subscribe("zigbee2mqtt/bridge/state", rx_bridge_availability)
            _bridge = True

    async def stop(self) -> None:
        await self.hal.unsubscribe(self.path)
        await super().stop()