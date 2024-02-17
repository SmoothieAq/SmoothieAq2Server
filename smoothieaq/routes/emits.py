import orjson
from fastapi import WebSocket, APIRouter
from fastapi.responses import HTMLResponse
from reactivex import operators as op

from ..device import devices
from ..div.emit import emit_to_transport
from ..util.rxutil import generator

router = APIRouter(
    prefix="/emits",
    responses={404: {"description": "Not found"}},
    tags=["emits"]
)


@router.websocket("/stream")
async def websocket_emits(websocket: WebSocket):
    await websocket.accept()
    try:
        rx_emits = devices.rx_all_observables.pipe(
            op.map(emit_to_transport),
            op.buffer_with_time_or_count(2, 5),
            op.map(orjson.dumps)
        )
        async for e in generator(rx_emits):
            await websocket.send_bytes(e)
    finally:
        await websocket.close()


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Test emits</title>
    </head>
    <body>
        <h1>emits</h1>
        <ul id='messages'>
        </ul>
        <script async>
            var ws = new WebSocket("ws://localhost:8000/emits/stream");
            ws.onmessage = async function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var data = await event.data.text()
                var content = document.createTextNode(data)
                message.appendChild(content)
                messages.appendChild(message)
            };
        </script>
    </body>
</html>
"""


@router.get("/stream-test")
async def get():
    return HTMLResponse(html)
