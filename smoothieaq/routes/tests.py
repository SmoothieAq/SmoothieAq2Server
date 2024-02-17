from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .. import devtest as dtest

router = APIRouter(
    prefix="/tests",
    responses={404: {"description": "Not found"}},
    tags=["tests"]
)


@router.get("/devtest")
async def devtest() -> HTMLResponse:
    await dtest.test()
    return HTMLResponse("")
