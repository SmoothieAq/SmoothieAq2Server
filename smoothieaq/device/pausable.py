from typing import Optional

import aioreactive as rx

from .expression import as_observable
from ..model.expression import Expr
from ..util.rxutil import AsyncBehaviorSubject


class Pausable:

    def __init__(self):
        self.paused: bool = False
        self._rx_paused_subject = AsyncBehaviorSubject[bool](self.paused)
        self.rx_paused: rx.AsyncObservable[bool] = self._rx_paused_subject
        self._rx_disposable: list[rx.AsyncDisposable] = []

    def init(self, deviceId: str, pauseExpr: Optional[Expr], ownerPaused: rx.AsyncObservable[bool]):
        if pauseExpr:
            self.rx_paused = rx.pipe(self.rx_paused,
                                     rx.combine_latest(as_observable(pauseExpr, deviceId)),
                                     rx.map(lambda bb: bb[0] or bb[1]))
        if ownerPaused:
            self.rx_paused = rx.pipe(self.rx_paused, rx.combine_latest(ownerPaused),
                                     rx.map(lambda bb: bb[0] or bb[1]))

    async def start(self):
        self._rx_disposable = await rx.pipe(self.rx_paused, rx.distinct_until_changed).subscribe_async(self.do_pause)

    async def stop(self):
        for d in self._rx_disposable:
            await d.dispose_async()
        self._rx_disposable = []

    async def do_pause(self, paused: bool):
        ...

    async def pause(self, paused: bool = True) -> None:
        self.paused = paused
        await self._rx_paused_subject.asend(paused)

    async def unpause(self) -> None:
        await self.pause(False)
