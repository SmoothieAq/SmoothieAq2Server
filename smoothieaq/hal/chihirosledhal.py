from .chihiroshal import ChihirosHal, Command
from .npwmhal import NPwmHal
from ..div.time import is_simulating


class ChihirosLedHal(ChihirosHal, NPwmHal):

    async def set_pwm(self, no: int, value: float):
        color_no = no
        brightness = int(value * 100)
        if not is_simulating():
            await self._command_subject.asend(Command(cmd_id=90, cmd_mode=7, parameters=[color_no, brightness]))
