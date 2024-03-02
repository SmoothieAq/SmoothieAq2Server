import time as t

from .emitdriver import EmitDriver, log
from ..div.emit import ObservableEmit


class LogEmitDriver(EmitDriver):
    id = "LogEmitDriver"

    def emit(self, e: ObservableEmit) -> None:
        log.info(
            f"{e.observable_id}: {e.value or ''}{e.enumValue or ''} {e.note or ''} "
            f"({t.strftime('%Y/%m/%d %H:%M:%S', t.localtime(e.stamp))})"
        )
