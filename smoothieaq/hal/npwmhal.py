from ..div.time import is_simulating
from ..hal.hal import Hal
from ..model.step import Program


class NPwmHal(Hal):

    def __init__(self) -> None:
        super().__init__()
        self._running_remote_program = False

    async def _set_pwm(self, no: int, value: float):
        raise NotImplemented()

    async def set_pwm(self, no: int, value: float):
        if not self._running_remote_program and not is_simulating():
            await self._set_pwm(no, value)

    async def _run_remote_program(self, program: Program, wanted_start_time: float):
        raise NotImplemented()

    async def run_remote_program(self, program: Program, wanted_start_time: float):
        # wanted_start_time should be in the past (at least, just so)
        if self._running_remote_program:
            await self.end_remote_program()
        self._running_remote_program = True
        await self._run_remote_program(program, wanted_start_time)

    async def _end_remote_program(self):
        raise NotImplemented()

    async def end_remote_program(self):
        if self._running_remote_program:
            self._running_remote_program = False
            await self._end_remote_program()
