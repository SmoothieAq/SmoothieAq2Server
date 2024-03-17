import logging
from dataclasses import dataclass

import aioreactive as rx
from expression.collections import Block, Map

from .driver import Driver, Status
from ..div.emit import RawEmit
from ..hal.npwmhal import NPwmHal
from ..util.rxutil import ix

log = logging.getLogger(__name__)


@dataclass
class ColorLed:
    id: str
    color_id: str
    no: int
    current_brightness: float
    saved_brightness: float


class LedDriver(Driver[NPwmHal]):
    id = "LedDriver"
    onOff_id = "A1"
    brightness_id = "A5"
    color_brightness_id = "2"

    def __init__(self):
        super().__init__()
        self.color_leds: Map[str, ColorLed] = Map.empty()

    def _init(self):
        super()._init()
        color_ids = self.params["colorIds"].split(":")

        def color_led(no: int) -> tuple[str, ColorLed]:
            color_id = color_ids[no]
            id = color_id + self.color_brightness_id
            return id, ColorLed(id, color_id, no, 0., 0.)

        self.color_leds = Map.of_block(Block.range(0, len(color_ids)).map(color_led))

    def _set_subjects(self) -> Map[str, rx.AsyncSubject]:
        return Map.of_block(
            self.color_leds.to_list().map(lambda i: i[1].id).append(Block.of(self.onOff_id, self.brightness_id)).map(
                lambda id: (id, rx.AsyncSubject[RawEmit]()))
        )

    async def set(self, rx_key: str, emit: RawEmit) -> None:
        log.debug(f"doing LedDriver.set({self.id}/{self.path}, {rx_key}, {emit})")
        assert self._rx_observers.__contains__(rx_key)

        if rx_key == self.onOff_id:
            await self.set_onoff(emit.enumValue)
        elif rx_key == self.brightness_id:
            await self.set_total_brightness(emit.value, 0.)
        else:
            await self.set_led_brightness(self.color_leds[rx_key], emit.value)

    async def set_onoff(self, enumValue: str):
        if enumValue == 'off':
            for cl in self.color_leds.values():
                cl.saved_brightness = cl.current_brightness
                await self.set_led_brightness(cl, 0.)
        elif enumValue == 'on' and ix(self.color_leds.values()).map(lambda cl: cl.current_brightness).sum() < 0.01:
            for cl in self.color_leds.values():
                await self.set_led_brightness(cl, cl.saved_brightness or 100.)

    async def set_total_brightness(self, value: float, currentValue: float):
        ...

    async def set_led_brightness(self, color_led: ColorLed, value: float):
        color_led.current_brightness = value
        try:
            await self.hal.set_pwm(color_led.no, value / 100)
        except Exception as ex:
            log.error(f"error on {self.path}",exc_info=ex)
            await self._status(Status.IN_ERROR, f"send error {ex}")
        await self._rx_observers[color_led.id].asend(RawEmit(value=value))
