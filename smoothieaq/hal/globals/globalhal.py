import aioreactive as rx

from smoothieaq.hal.hal import Hal


class GlobalHal(Hal):

    def __init__(self):
        self.start_count = 0

    async def global_start(self):
        pass

    async def start(self):
        self.start_count += 1
        if self.start_count == 1:
            await self.global_start()

    async def global_stop(self):
        pass

    async def stop(self):
        self.start_count -= 1
        if self.start_count == 0:
            await self.global_stop()

