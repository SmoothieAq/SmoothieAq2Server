import locale
import os
from _locale import LC_ALL, LC_MESSAGES

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import drivers, emits, tests
from .div import objectstore as ostore
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ostore.load()
    yield


app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drivers.router)
app.include_router(emits.router)
app.include_router(tests.router)


@app.get("/")
async def root() -> str:
    return "SmoothieAq v2.0 dev"
