from typing import Any

import aioreactive as rx
from starlette.websockets import WebSocketState, WebSocketDisconnect
from fastapi import WebSocket


async def websocket_stream(websocket: WebSocket, rx_stream: rx.AsyncObservable[Any]):
    await websocket.accept()
    try:
        obv = rx.AsyncIteratorObserver(rx_stream)
        async with await rx_stream.subscribe_async(obv) as subscription:
            prev = None
            async for e in obv:
                if not websocket.client_state == WebSocketState.CONNECTED:
                    break
                try:
                    if e != prev:
                        await websocket.send_json(e)
                    prev = e
                except WebSocketDisconnect:
                    break

    finally:
        if not websocket.client_state == WebSocketState.DISCONNECTED:
            try:
                await websocket.close()
            except:
                return


def stream_test_html(p: str) -> str:
    return """
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
            var ws = new WebSocket("ws://localhost:8000/""" + p + """/stream");
            ws.onmessage = async function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var data = await event.data
                var content = document.createTextNode(data)
                message.appendChild(content)
                messages.appendChild(message)
            };
        </script>
    </body>
</html>
"""
