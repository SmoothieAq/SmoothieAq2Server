import logging
from typing import Optional

from .driver import Driver, Status
from ..div.emit import RawEmit
from ..model import thing as aqt
from .chihiros.chihirosctl import set_brightness
from ..div.time import is_simulating
import reactivex as rx

log = logging.getLogger(__name__)


class ChihirosLedDriver(Driver):
    id = "ChihirosLedDriver"

    def __init__(self, m_driver: aqt.Driver):
        super().__init__(m_driver)
        self.color_ids: list[str] = []
        self.color_no: dict[str, int] = {}
        self.current_brightness: list[int] = []

    def _init(self):
        super()._init()
        n = 0
        for c in self.params["colorIds"]:
            self.color_ids.append(c)
            self.color_no[c] = n
            n = n + 1
            self.current_brightness.append(0)

    def _set_subjects(self) -> dict[str, rx.subject.Subject]:
        return dict(map(lambda id: (id, rx.Subject[RawEmit]()), ["A"] + [c + "1" for c in self.color_ids]))

    def start(self) -> None:
        super().start()
        self._status(Status.RUNNING)

    def set(self, rx_key: str, emit: RawEmit) -> None:
        print("??",emit)
        log.debug(f"doing chihirosDriver.set({self.id}/{self.path}, {rx_key}, {emit})")
        assert self._rx_observers.__contains__(rx_key)
        brightness = int(emit.value)
        color_no = self.color_no[rx_key[0:1]]
        if not is_simulating():
            print("!!",color_no,brightness)
            set_brightness(self.path, color_no, brightness)
        self.current_brightness[color_no] = brightness
        self._rx_observers[rx_key].on_next(RawEmit(value=float(brightness)))
