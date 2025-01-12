import logging

import orjson
from fastapi import WebSocket, APIRouter
from fastapi.responses import HTMLResponse
import aioreactive as rx

from ..device import devices
from ..div.emit import emit_to_transport
from ..util import rxutil as ix
from ..routes import streamutil

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/emits",
    responses={404: {"description": "Not found"}},
    tags=["emits"]
)


@router.websocket("/stream")
async def websocket_emits(websocket: WebSocket):
    rx_emits: rx.AsyncObservable[bytes] = rx.pipe(
        devices.rx_all_observables,
        rx.map(emit_to_transport),
        ix.buffer_with_time(2, 5),
        rx.filter(lambda l: len(l) > 0),
        rx.map(orjson.dumps)
    )
    await streamutil.websocket_stream(websocket, rx_emits)


@router.get("/stream-test")
async def get():
    return HTMLResponse(streamutil.stream_test_html("emits"))
