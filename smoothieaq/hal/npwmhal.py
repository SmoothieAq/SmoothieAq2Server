from smoothieaq.hal.hal import Hal


class NPwmHal(Hal):

    async def set_pwm(self, no: int, value: float):
        raise NotImplemented()
