import logging
import os
import tempfile
import time
from typing import Type, AsyncIterator

import aiosqlite
from expression.collections import Seq

from smoothieaq.modelobject.objectpersister import ObjectPersister
from smoothieaq.util.rxutil import ix

log = logging.getLogger(__name__)

db_file: str = os.environ.get("smoothieaq_db", os.path.join(tempfile.gettempdir(),"smoothieaq11.db"))

class ObjectSqlite(ObjectPersister):

    async def create_db_if_needed(self) -> bool: # True if new db
        log.info(f"Sqlite database {db_file}")
        async with aiosqlite.connect(db_file) as db:
            async with db.execute("SELECT count(*) FROM sqlite_schema WHERE tbl_name = 'smoothieaq_object'") as cursor:
                async for row in cursor:
                    if row[0] >= 1:
                        log.info("Found existing smoothieaq_object table")
                        return False
            log.info("Creating new smoothieaq_object table")
            await db.execute(
                "CREATE TABLE smoothieaq_object ("
                "  type TEXT,"
                "  id TEXT,"
                "  stamp timestamp,"
                "  json TEXT"
                ")")
            await db.execute(
                "CREATE UNIQUE INDEX smoothieaq_object_prim ON smoothieaq_object("
                "  type,"
                "  id"
                ")")
            await db.commit()
            return True


    async def get_all(self, type: Type) -> Seq[str]:
        jsons: list[str] = []
        async with aiosqlite.connect(db_file) as db:
            async with db.execute(
                "SELECT json FROM smoothieaq_object WHERE type = ?",
                (str(type),)
            ) as cursor:
                async for row in cursor:
                    jsons.append(row[0])
            return ix(jsons)


    async def get(self, type: Type, id: str) -> str:
        async with aiosqlite.connect(db_file) as db:
            async with db.execute(
                "SELECT json FROM smoothieaq_object WHERE type = ? AND id = ?",
                (str(type), id)
            ) as cursor:
                async for row in cursor:
                    return row[0]
            raise KeyError

    async def create(self, type: Type, id: str, json: str) -> None:
        async with aiosqlite.connect(db_file) as db:
            await db.execute(
                "INSERT INTO smoothieaq_object VALUES (?, ?, ?, ?)",
                (str(type), id, time.time(), json)
            )
            log.info(f"Create {type} {id}")
            await db.commit()


    async def update(self, type: Type, id: str, json: str) -> None:
        async with aiosqlite.connect(db_file) as db:
            await db.execute(
                "UPDATE smoothieaq_object SET (stamp = ?, json = ?)"
                "  WHERE typoe = ? AND id = ?",
                (time.time(), json, str(type), id)
            )
            log.info(f"update {type} {id}")
            await db.commit()
