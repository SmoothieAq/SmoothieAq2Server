import logging
import os
import tempfile
import time as t
from typing import Optional

from pymysql import TimestampFromTicks

from .emitdriver import EmitDriver
from ..div.emit import ObservableEmit
from ..model import thing as aqt

import aiomysql

log = logging.getLogger(__name__)


class MariadbEmitDriver(EmitDriver):
    id = "MariadbEmitDriver"

    def __init__(self, m_driver: aqt.EmitDriver) -> None:
        super().__init__(m_driver)
        self.host: Optional[str] = '127.0.0.1'
        self.port: Optional[str] = '3306'
        self.user: Optional[str] = 'root'
        self.password: Optional[str] = None
        self.db: Optional[str] = 'smoothieaq'
        self.connection: Optional[aiomysql.Connection] = None

    def _init(self):
        super()._init()
        self.host = self.params.get('host', self.host)
        self.port = self.params.get('port', self.port)
        self.user = self.params.get('user', self.user)
        self.db = self.params.get('db', self.db)
        self.password = self.params.get('password')

    async def create_if_needed(self):
        cur = None
        try:
            cur = await self.connection.cursor()
            await cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'smoothieaq_emits'")
            rows = await cur.fetchall()
            if rows[0][0] >= 1:
                log.info("Found existing smoothieaq_emits table")
                return
            log.info("Creating new smoothieaq_emits table")
            await cur.execute(
                "CREATE TABLE smoothieaq_emits ("
                "  observable_id varchar(10),"
                "  stamp timestamp,"
                "  value FLOAT,"
                "  enumValue varchar(254),"
                "  note varchar(2000)"
                ")")
            await self.connection.commit()
        except Exception as e:
            log.error("Trying to create table", exc_info=e)
        if cur: await cur.close()

    async def start(self):
        await super().start()
        log.info(f"Sqlite database {self.host}  {self.port}")
        self.connection = await aiomysql.connect(host=self.host, port=int(self.port), user=self.user, password=self.password, db=self.db)
        await self.create_if_needed()

    async def stop(self) -> None:
        await self.connection.close()
        await super().stop()

    async def emit(self, emits: list[ObservableEmit]) -> None:
        cur = None
        try:
            cur = await self.connection.cursor()
            emit_values = [(e.observable_id, TimestampFromTicks(e.stamp), e.value, e.enumValue, e.note) for e in emits]
            await cur.executemany("INSERT INTO smoothieaq_emits (observable_id, stamp, value, enumValue, note) VALUES (%s, %s, %s, %s, %s)", emit_values)
            await self.connection.commit()
        except Exception as e:
            log.error("Trying to insert", exc_info=e)
        if cur: await cur.close()
