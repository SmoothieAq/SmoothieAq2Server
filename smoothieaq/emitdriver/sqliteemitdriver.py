import logging
import os
import tempfile
import time as t
from typing import Optional

from .emitdriver import EmitDriver
from ..div.emit import ObservableEmit
from ..model import thing as aqt

import aiosqlite

log = logging.getLogger(__name__)


class SqliteEmitDriver(EmitDriver):
    id = "SqliteEmitDriver"

    def __init__(self, m_driver: aqt.EmitDriver) -> None:
        super().__init__(m_driver)
        self.db_file: str = os.path.join(tempfile.gettempdir(),"smoothieaq-emits.db")
        self.connection: Optional[aiosqlite.Connection] = None

    def _init(self):
        super()._init()
        self.db_file = self.params.get('db_file', self.db_file)

    async def create_if_needed(self):
        async with self.connection.execute("SELECT count(*) FROM sqlite_schema WHERE tbl_name = 'smoothieaq_emits'") as cursor:
            async for row in cursor:
                if row[0] >= 1:
                    log.info("Found existing smoothieaq_emits table")
                    return
        log.info("Creating new smoothieaq_emits table")
        await self.connection.execute(
            "CREATE TABLE smoothieaq_emits ("
            "  observable_id TEXT,"
            "  stamp timestamp,"
            "  value FLOAT,"
            "  enumValue TEXT,"
            "  note TEXT"
            ")")
        await self.connection.commit()

    async def start(self):
        await super().start()
        log.info(f"Sqlite database {self.db_file}")
        self.connection = await aiosqlite.connect(self.db_file)
        await self.create_if_needed()

    async def stop(self) -> None:
        await self.connection.close()
        await super().stop()

    async def emit(self, emits: list[ObservableEmit]) -> None:
        emit_values = [(e.observable_id, e.stamp, e.value, e.enumValue, e.note) for e in emits]
        await self.connection.executemany("INSERT INTO smoothieaq_emits VALUES (?, ?, ?, ?, ?)", emit_values)
        await self.connection.commit()
