import logging
from typing import Optional, Callable, Awaitable

from expression.collections import Map

log = logging.getLogger(__name__)


class Hal:

    def __init__(self) -> None:
        self.path: Optional[str] = None
        self.params: Optional[Map[str, str]] = None
        self.error_handler: Optional[Callable[[str], Awaitable[None]]] = None

    def init(self, path: Optional[str], params: Map[str, str], error_handler: Callable[[str], Awaitable[None]] = None):
        self.path = path
        self.params = params
        self.error_handler = error_handler

    async def start(self):
        pass

    async def stop(self):
        pass

    async def _error(self, ex: Exception):
        log.error(f"hal error {self.path}", exc_info=ex)
        if self.error_handler:
            await self.error_handler(f"hal error {ex}")


class NoHal(Hal):
    pass
