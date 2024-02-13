import copy

from fastapi import APIRouter, HTTPException
from ..driver.drivers import *
from ..model import thing as aqt

router = APIRouter(
    prefix="/drivers",
    responses={404: {"description": "Not found"}}
)


@router.get("/")
async def get_drivers() -> list[aqt.Driver]:
    """
    Get basic information on all drivers.

    To get all information about a driver use /drivers/{driver_id}.

    :return: A list of information about all known drivers, but without the templateDevice
    """

    def driver_without_template_device(m_driver: aqt.Driver):
        d = copy.deepcopy(m_driver)
        d.templateDevice = None
        return d

    return list(map(driver_without_template_device, get_m_drivers()))


@router.get("/{driver_id}")
async def get_driver(driver_id: str) -> aqt.Driver:
    try:
        return get_m_driver(driver_id)
    except KeyError:
        raise HTTPException(404, f"Driver {driver_id} not found")
