from typing import Type

from expression.collections import Seq

from smoothieaq.util.rxutil import ix


class ObjectPersister:

    async def create_db_if_needed(self) -> bool: # True if new db
        return True


    async def get_all(self, type: Type) -> Seq[str]:
        return ix([])


    async def get(self, type: Type, id: str) -> str:
        raise KeyError


    async def create(self, type: Type, id: str, json: str) -> None:
        pass


    async def update(self, type: Type, id: str, json: str) -> None:
        pass
