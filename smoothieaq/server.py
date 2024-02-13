from fastapi import FastAPI
from .routes import drivers
from smoothieaq import objectstore as os
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.load()
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(drivers.router)


@app.get("/")
async def root() -> str:
    return "SmoothieAq v2.0 dev"
