import logging
from dataclasses import dataclass
from typing import Optional

import aioreactive as rx
from expression.collections import Block, Map

from .driver import Driver, Status
from .chihiros.chihirosctl import ChihirosCtl
from ..div.emit import RawEmit
from ..div.time import is_simulating

log = logging.getLogger(__name__)


@dataclass
class Color_led:
    id: str
    color_id: str
    no: int
    current_brightness: float


class ChihirosLedDriver(Driver):
    id = "ChihirosLedDriver"
    onOff_id = "A1"
    brightness_id = "A5"
    color_brightness_id = "2"

    def __init__(self):
        super().__init__()
        self.color_leds: Map[str, Color_led] = Map.empty()
        self.chihiros_ctl: Optional[ChihirosCtl] = None

    def _init(self):
        super()._init()
        color_ids = self.params["colorIds"].split(":")

        def color_led(no: int) -> tuple[str, Color_led]:
            color_id = color_ids[no]
            id = color_id + self.color_brightness_id
            return id, Color_led(id, color_id, no, 0.)

        self.color_leds = Map.of_block(Block.range(0, len(color_ids)).map(color_led))
        self.chihiros_ctl = ChihirosCtl(self.path)

    def _set_subjects(self) -> Map[str, rx.AsyncSubject]:
        return Map.of_block(
            self.color_leds.to_list().map(lambda i: i[1].id).append(Block.of(self.onOff_id, self.brightness_id)).map(
                lambda id: (id, rx.AsyncSubject[RawEmit]()))
        )

    async def start(self) -> None:
        await super().start()
        if not is_simulating():
            await self.chihiros_ctl.start()
        await self._status(Status.RUNNING)

    async def stop(self) -> None:
        if not is_simulating():
            await self.chihiros_ctl.stop()
        await super().stop()

    async def set(self, rx_key: str, emit: RawEmit) -> None:
        log.debug(f"doing chihirosDriver.set({self.id}/{self.path}, {rx_key}, {emit})")
        assert self._rx_observers.__contains__(rx_key)

        if rx_key == self.onOff_id:
            return

        if rx_key == self.brightness_id:
            return

        brightness = int(emit.value)
        color_led = self.color_leds[rx_key]
        if not is_simulating():
            await self.chihiros_ctl.set_brightness(color_led.no, int(brightness))
        color_led.current_brightness = brightness
        await self._rx_observers[rx_key].asend(RawEmit(value=float(brightness)))
