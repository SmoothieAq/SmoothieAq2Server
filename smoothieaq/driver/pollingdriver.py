from typing import Optional

import reactivex as rx
from reactivex import operators as op
from reactivex.disposable import Disposable

from .driver import Driver, log
from ..model import thing as aqt
from ..div import time


class PollingDriver(Driver):
    polling_key: str = 'pollEverySeconds'

    def __init__(self, m_driver: aqt.Driver):
        super().__init__(m_driver)
        self.pollEverySeconds: Optional[float] = None
        self.polling_disposable: Optional[Disposable] = None

    def _init(self):
        super()._init()
        self.pollEverySeconds = float(self.params[self.polling_key])

    def start(self) -> None:
        super().start()
        duration = time.duration(self.pollEverySeconds)
        log.debug(f"doing driver.pollingEvery({self.id}/{self.path}, {duration})")
        self.polling_disposable = (
            rx.interval(duration)
            .pipe(op.delay_subscription(0.5))
            .subscribe(lambda n: self.poll())
        )

    def stop(self) -> None:
        super().stop()
        if self.polling_disposable:
            self.polling_disposable.dispose()
