from typing import Optional
from datetime import datetime, timezone
import time as t

import reactivex as rx
from reactivex import operators as op
from reactivex.disposable import Disposable

from .driver import Driver, log, Status
from ..div.emit import RawEmit
from ..model import thing as aqt
from ..div import time


class TimeDriver(Driver):
    id = "TimeDriver"
    rx_key: str = 'A'

    def __init__(self, m_driver: aqt.Driver):
        super().__init__(m_driver)
        self.polling_disposable: Optional[Disposable] = None

    def _set_subjects(self) -> dict[str, rx.subject.Subject]:
        return {self.rx_key: rx.Subject[RawEmit]()}

    def start(self) -> None:
        super().start()
        duration = time.duration(60.)
        first = int(t.time() / duration) * duration + duration

        def tick(at):
            self._rx_observers[self.rx_key].on_next(RawEmit(value=time.time(), enumValue="tick"))
            next = at + duration
            self.polling_disposable.dispose()
            self.polling_disposable = rx.timer(next - t.time()).subscribe(lambda n: tick(next))
        self.polling_disposable = rx.timer(first - t.time()).subscribe(lambda n: tick(first))
        self._status(Status.RUNNING)

    def stop(self) -> None:
        super().stop()
        if self.polling_disposable:
            self.polling_disposable.dispose()
