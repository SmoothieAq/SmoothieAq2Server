import time
from asyncio import sleep
from typing import cast

import reactivex

import smoothieaq.model.thing as aqt
import smoothieaq.objectstore as os
import smoothieaq.model.expression as e
from smoothieaq.device import devices as dv
from smoothieaq.device.device import *
from smoothieaq.driver import drivers as dr


async def test():

    os.load()

    dv.rx_all_observables.subscribe(lambda e: print(
        f"{e.observable_id}: {e.value or ''}{e.enumValue or ''} {e.note or ''} ({time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(e.stamp))}) {e.stamp}"
    ))

    dr1 = dr.find_driver("DummyDriver")
    dr2 = dr.find_driver("PsutilDriver")
    dr3 = dr.find_driver("MemoryMeasureDriver")
    dr4 = dr.find_driver("MemoryStateDriver")

    mdv1 = dr1.create_m_device()
    mdv1.driver.params[0].value = "1.5"
    mdv1.driver.params[1].value = "7.2"
    mdv1.driver.params[2].value = "0.4"
    dv.create_new_device(mdv1)

    mdv2 = dr2.create_m_device()
    mdv2.driver.params[0].value = "2"
    dv.create_new_device(mdv2)

    mdv4 = dr3.create_m_device()
    id4 = dv.create_new_device(mdv4)

    mdv5 = dr4.create_m_device()
    cast(aqt.State,mdv5.observables[0]).setExpr = e.RxOp1Expr(e.RxOp1.THROTTLE,3,e.RxOp0Expr(e.RxOp0.DISTINCT,e.IfExpr(
        ifExpr=e.BinaryOpExpr(expr1=e.ObservableExpr(observableRef="1:A"),op=e.BinaryOp.GT,expr2=e.ValueExpr(7.3)),
        thenExpr=e.EnumValueExpr("on"),
        elseExpr=e.EnumValueExpr("off")
    )))
    dv.create_new_device(mdv5)

    await sleep(10)
    cast(Measure, dv.get_observable(id4+":A")).measurement(99)

    mdv3 = dr1.create_m_device()
    mdv3.driver.params[0].value = "1"
    mdv3.driver.params[1].value = "25"
    mdv3.driver.params[2].value = "0.9"
    dv.create_new_device(mdv3)

    await sleep(6)

    # await sleep(4)
    # d.observables['A'].pause()
    # await sleep(4)
    # d.observables['A'].unpause()
    # await sleep(4)
    # d.pause()
    # await sleep(4)
    # d.unpause()
    # await sleep(4)
