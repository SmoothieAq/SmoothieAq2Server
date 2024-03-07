import logging
from typing import Optional

from ..div.emit import ObservableEmit
from ..model import thing as aqt


log = logging.getLogger(__name__)


class EmitDriver:
    id: str

    def __init__(self, m_driver: aqt.EmitDriver) -> None:
        self.m_driver = m_driver
        self.path: Optional[str] = None
        self.params: Optional[dict[str, str]] = None

    def create_m_device(self) -> aqt.EmitDevice:
        return self.m_driver.templateDevice

    def _init(self):
        pass

    async def init(self, path: str, params: dict[str, str]) -> 'EmitDriver':
        log.info(f"doing emitDriver.init({self.id}/{path})")
        self.path = path
        self.params = params
        self._init()
        return self

    async def emit(self, emits: list[ObservableEmit]) -> None:
        log.error("emit() not implemented")
        raise Exception("emit() not implemented")
