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
    prefix="/observables",
    responses={404: {"description": "Not found"}},
    tags=["observables"]
)


@router.websocket("/{observable_id}/stream")
async def websocket_emits(websocket: WebSocket, observable_id: str):
    try:
        rx_observable = d.get_rx_observable(observable_id)
        if rx_observable is None:
            raise KeyError
        rx_emits: rx.AsyncObservable[bytes] = rx.pipe(
            rx_observable,
            rx.map(emit_to_transport),
            ix.buffer_with_time(0.2, 3),
            rx.filter(lambda l: len(l) > 0),
            rx.map(orjson.dumps)
        )
        await streamutil.websocket_stream(websocket, rx_emits)
    except KeyError:
        raise HTTPException(404, f"Observable {observable_id} not found")


@router.get("/{observable_id}/stream-test")
async def get(observable_id: str):
    print(f"!!**!! {observable_id}")
    return HTMLResponse(streamutil.stream_test_html(f"observables/{observable_id}"))


def _observable(observable_id: str) -> d.Observable:
    try:
        return d.get_observable(observable_id)
    except KeyError:
        raise HTTPException(404, f"Observable {observable_id} not found")


@router.get("/{observable_id}", response_model_exclude_none=True)
async def get_observable(observable_id: str,) -> aqt.Observable:
    return _observable(observable_id).m_observable


@router.get("/{observable_id}/value")
async def get_value(observable_id: str,) -> RawEmit:
    return emit_to_raw(_observable(observable_id).current_value)


@router.get("/{observable_id}/status")
async def get_status(observable_id: str,) -> RawEmit:
    return emit_to_raw(_observable(observable_id).current_status)


@router.post("/{observable_id}/pause")
async def post_pause(observable_id: str,) -> None:
    await _observable(observable_id).pause()


@router.post("/{observable_id}/unpause")
async def post_unpause(observable_id: str,) -> None:
    await _observable(observable_id).unpause()


@router.post("/{observable_id}/measurement")
async def post_measurement(observable_id: str, emit: RawEmit) -> None:
    await _observable(observable_id).measurement(emit.value, emit.note)


@router.post("/{observable_id}/set-value")
async def post_set_value(observable_id: str, emit: RawEmit) -> None:
    await _observable(observable_id).set_value(emit)


@router.post("/{observable_id}/add")
async def post_add(observable_id: str, emit: RawEmit) -> None:
    await _observable(observable_id).add(emit.value, emit.note)


@router.post("/{observable_id}/reset")
async def post_reset(observable_id: str, emit: RawEmit) -> None:
    await _observable(observable_id).reset(emit.note)


@router.post("/{observable_id}/fire")
async def post_fire(observable_id: str, emit: RawEmit) -> None:
    await _observable(observable_id).fire(emit)


