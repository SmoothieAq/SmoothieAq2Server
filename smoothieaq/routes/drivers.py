import copy
from typing import Annotated

from fastapi import APIRouter, HTTPException, Header

from ..driver.drivers import *
from ..model import thing as aqt

router = APIRouter(
    prefix="/drivers",
    responses={404: {"description": "Not found"}},
    tags=["drivers"]
)


@router.get("/", response_model_exclude_none=True)
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

    return list(map(driver_without_template_device, await get_m_drivers()))


@router.get("/{driver_id}", response_model_exclude_none=True)
async def get_driver(
        driver_id: str,
        accept_language: Annotated[str | None, Header()] = None
) -> aqt.Driver:
    print("***", accept_language)
    try:
        return await get_m_driver(driver_id)
    except KeyError:
        raise HTTPException(404, f"Driver {driver_id} not found")


@router.post("/")
async def post_driver(driver: aqt.Driver) -> str:
    return await put_m_driver(driver)


@router.put("/{driver_id}")
async def put_driver(driver_id: str, driver: aqt.Driver) -> None:
    await update_m_driver(driver)
