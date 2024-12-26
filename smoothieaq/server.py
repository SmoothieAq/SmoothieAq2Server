import locale
import os
from _locale import LC_ALL, LC_MESSAGES

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import drivers, emits, tests
from .div import objectstore as ostore
from contextlib import asynccontextmanager

from smoothieaq.devtest import *
#from smoothieaq.bletest import *
import logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("smoothieaq").setLevel(logging.INFO)
    logging.getLogger("smoothieaq.hal").setLevel(logging.DEBUG)
    logging.getLogger("smoothieaq.driver.driver").setLevel(logging.INFO)
    logging.info("info")
    await ostore.load()
    await sleep(1)
    #t.simulate(speed=10)
    await test()
#    await ostore.load()
    yield


app = FastAPI(lifespan=lifespan, separate_input_output_schemas=False)

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
