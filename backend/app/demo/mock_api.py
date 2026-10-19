import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/demo", tags=["controlled demo targets"])


@router.get("/healthy")
def healthy() -> dict[str, str]:
    return {"status": "success"}


@router.get("/server-error")
def server_error() -> JSONResponse:
    return JSONResponse(status_code=500, content={"status": "error", "scenario": "controlled-server-error"})


@router.get("/slow")
async def slow() -> dict[str, str]:
    await asyncio.sleep(3)
    return {"status": "success", "scenario": "controlled-slow-response"}


@router.get("/business-error")
def business_error() -> dict[str, str]:
    return {"status": "error", "scenario": "controlled-business-error"}

