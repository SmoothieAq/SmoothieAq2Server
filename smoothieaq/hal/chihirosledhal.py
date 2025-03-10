from datetime import datetime

from .chihiroshal import ChihirosHal, Command
from .npwmhal import NPwmHal
from ..model.step import Program
from ..util.timeutil import time_length
from ..div.time import time as div_time, duration


class ChihirosLedHal(ChihirosHal, NPwmHal):

    async def _set_pwm(self, no: int, value: float):
        color_no = no
        brightness = int(round(value * 100))
        await self._command_subject.asend(Command(cmd_id=90, cmd_mode=7, parameters=[color_no, brightness])) # manual set

    async def _run_remote_program(self, program: Program, wanted_start_time: float):
        color_ids = self.params["colorIds"].split(":")

        now = div_time()
        assert now >= wanted_start_time
        length = time_length(program.length).total_seconds()
        stop_time = wanted_start_time + length

        nowt = datetime.fromtimestamp(div_time())
        await self._command_subject.asend(Command(cmd_id=90, cmd_mode=9,
                parameters=[nowt.year - 2000, nowt.month, nowt.isoweekday(), nowt.hour, nowt.minute, nowt.second])) # set time

        startt = datetime.fromtimestamp(wanted_start_time)
        stopt = datetime.fromtimestamp(stop_time)
        transm = 0
        if program.transition and program.transition.length:
            transm = int(time_length(program.transition.length).total_seconds()/60)

        values = [255, 255, 255, 255, 255, 255, 255, 255]
        for val in program.values:
            for i in range(len(color_ids)):
                if val.id[0] == color_ids[i]:
                    values[i]  = int(val.value)

        await self._command_subject.asend(Command(cmd_id=165, cmd_mode=25,
                parameters=[startt.hour, startt.minute, stopt.hour, stopt.minute, transm, 128, *values])) # auto mode


    async def _end_remote_program(self):
        await self._command_subject.asend(Command(cmd_id=90, cmd_mode=5, parameters=[5, 255, 255])) # reset auto mode

