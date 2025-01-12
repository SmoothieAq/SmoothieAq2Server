import orjson
from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import HTMLResponse
import aioreactive as rx

from ..device import devices as d
from ..div.emit import emit_to_transport, RawEmit, emit_to_raw
from ..model import thing as aqt
from ..util import rxutil as ix
from ..routes import streamutil

router = APIRouter(
    prefix="/devices",
    responses={404: {"description": "Not found"}},
    tags=["devices"]
)


@router.get("/", response_model_exclude_none=True)
async def get_devices() -> list[aqt.Device]:
    """
    Get information on all devices.
    :return: A list of all known devices
    """

    return list(d.get_devices().map(lambda d: d.m_device))


@router.websocket("/stream")
async def websocket_emits(websocket: WebSocket):
    rx_emits: rx.AsyncObservable[bytes] = rx.pipe(
        d.get_rx_device_updates(),
        rx.map(lambda d: d.m_device),
        ix.buffer_with_time(0.5, 10),
        rx.filter(lambda l: len(l) > 0),
        rx.map(orjson.dumps)
    )
    await streamutil.websocket_stream(websocket, rx_emits)


@router.get("/stream-test")
async def get():
    return HTMLResponse(streamutil.stream_test_html("devices"))


def _device(device_id: str,) -> d.Device:
    try:
        return d.get_device(device_id)
    except KeyError:
        raise HTTPException(404, f"Device {device_id} not found")


@router.get("/{device_id}", response_model_exclude_none=True)
async def get_device(device_id: str,) -> aqt.Device:
    return _device(device_id).m_device


@router.get("/{device_id}/status")
async def get_status(device_id: str,) -> RawEmit:
    return emit_to_raw(_device(device_id).current_status)


@router.post("/{device_id}/poll")
async def post_poll(device_id: str,) -> None:
    await _device(device_id).poll()


@router.post("/{device_id}/pause")
async def post_pause(device_id: str,) -> None:
    await _device(device_id).pause()


@router.post("/{device_id}/unpause")
async def post_unpause(device_id: str,) -> None:
    await _device(device_id).unpause()


@router.post("/")
async def post_device(device: aqt.Device) -> str:
    return await d.create_new_device(device)


@router.put("/{device_id}")
async def put_device(device_id: str, device: aqt.Device) -> None:
    _device(device_id)
    await d.update_device(device)
