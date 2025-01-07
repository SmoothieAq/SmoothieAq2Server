import copy

from fastapi import APIRouter, HTTPException

from ..device import devices as d
from ..model import thing as aqt

router = APIRouter(
    prefix="/devices",
    responses={404: {"description": "Not found"}},
    tags=["devices"]
)


def device_without_details(m_device: aqt.Device):
    d: aqt.Device = copy.deepcopy(m_device)
    d.observables = None
    d.pausedIf = None
    d.pauseExpr = None
    d.schedules = None
    return d


@router.get("/", response_model_exclude_none=True)
async def get_devices() -> list[aqt.Device]:
    """
    Get basic information on all devices.

    To get all information about a device use /device/{device_id}.

    :return: A list of information about all known devices, but without the observables, etc
    """

    return list(d.get_devices().map(lambda d: d.m_device).map(device_without_details))


@router.get("/{device_id}", response_model_exclude_none=True)
async def get_device(device_id: str,) -> aqt.Device:
    try:
        return d.get_device(device_id).m_device
    except KeyError:
        raise HTTPException(404, f"Device {device_id} not found")


@router.post("/")
async def post_device(device: aqt.Device) -> str:
    return await d.create_new_device(device)


@router.put("/{device_id}")
async def put_device(device: aqt.Device) -> None:
    await d.update_device(device)
