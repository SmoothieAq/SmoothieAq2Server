import logging

import aioreactive as rx

from smoothieaq.hal.hal import Hal


log = logging.getLogger(__name__)


class GlobalHal(Hal):

    def __init__(self):
        self.start_count = 0

    async def global_start(self):
        pass

    async def start(self):
        self.start_count += 1
        if self.start_count == 1:
            log.info("global_start {self.path}")
            await self.global_start()

    async def global_stop(self):
        pass

    async def stop(self):
        self.start_count -= 1
        if self.start_count == 0:
            log.info("global_start {self.path}")
            await self.global_stop()

