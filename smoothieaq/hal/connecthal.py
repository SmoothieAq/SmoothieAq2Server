import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

import aioreactive as rx
from aioreactive.create import interval
from expression.collections import Map

from smoothieaq.hal.hal import Hal

log = logging.getLogger(__name__)


@dataclass
class AbstractCommand:
    ...


class ConnectHal[Command: AbstractCommand](Hal):

    def __init__(self) -> None:
        super().__init__()
        self.keep_connected_secs = 10
        self._command_subject: Optional[rx.AsyncSingleSubject[Command | None | int]] = None
        self._command_disposable: Optional[rx.AsyncDisposable] = None

    def init(self, path: Optional[str], params: Map[str, str], error_handler: Callable[[str], Awaitable[None]] = None):
        super().init(path, params, error_handler)
        self.keep_connected_secs = params.get("keep_connected_secs", 10)

    def _ctl(self) -> Callable[[Command | None | int], Awaitable[None]]:
        hal_connection = self.create_hal_connection()

        async def _(c: Command | None | int) -> None:
            try:
                match c:
                    case None:
                        await hal_connection.disconnect()
                    case int():
                        await hal_connection.disconnect_if_timeout()
                    case _:
                        await hal_connection.do_command(c)
            except Exception as ex:
                await self._error(ex)

        return _

    def create_hal_connection(self) -> '_HalConnection[Command, ConnectHal]':
        raise NotImplemented()

    async def start(self):
        await super().start()
        self._command_subject = rx.AsyncSubject[Command | None | int]()
        self._command_disposable = await rx.pipe(
            self._command_subject,
            rx.merge(interval(self.keep_connected_secs, self.keep_connected_secs))
        ).subscribe_async(self._ctl())

    async def stop(self):
        await self._command_subject.asend(None)  # to disconnect
        await self._command_subject.aclose()
        self._command_subject = None
        await self._command_disposable.dispose_async()
        await super().stop()


class _HalConnection[Command: AbstractCommand, Connect: ConnectHal[AbstractCommand]]:

    def __init__(self, connectHal: Connect):
        self.connectHal = connectHal
        self.last_time: float = 0
        self.disconnecting = False

    def is_connected(self) -> bool:
        ...

    async def connect(self):
        if not self.is_connected():
            self.disconnecting = False
            self.last_time = time.time()
            await self.do_connect()

    async def do_connect(self):
        ...

    async def disconnect(self):
        if self.is_connected():
            self.disconnecting = True
            await self.do_disconnect()

    async def do_disconnect(self):
        ...

    async def disconnect_if_timeout(self):
        if self.is_connected() and self.last_time + self.connectHal.keep_connected_secs < time.time():
            await self.disconnect()

    async def do_command(self, command: Command):
        if not self.is_connected():
            await self.connect()
        self.last_time = time.time()
