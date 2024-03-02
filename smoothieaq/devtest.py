from asyncio import sleep
from typing import cast

import smoothieaq.model.expression as e
from smoothieaq.device import devices as dv
from smoothieaq.device.device import *
from smoothieaq.driver import drivers as dr
from .emitdriver import emitdrivers as edr
from .emitdevice import emitdevices as edv
from smoothieaq.div import time
import time as t


async def test():

    #time.simulate(speed=10)

    dv.rx_all_observables.subscribe(on_next=lambda e: print(
        f"{e.observable_id}: {e.value or ''}{e.enumValue or ''} {e.note or ''} ({t.strftime('%Y/%m/%d %H:%M:%S',t.localtime(e.stamp))}) {e.stamp}"
    ),on_error=lambda ex: print("error",ex))

    dv.create_new_device(dr.find_driver("TimeDriver").create_m_device())

    if False:
        drch = dr.find_driver("ChihirosLedDriver")
        mdvch = drch.create_m_device(aqt.DriverRef(path="C21C06F8-D0E0-DC60-7D78-D8BBFCF23DAD", params=[aqt.Param(key="colorIds", value="RG")]))
        dvch = dv.create_new_device(mdvch)

        await sleep(1)

        cast(Amount, dv.get_observable(dvch + ":W1")).set_value(15.)

    await sleep(60)

    if False:
        dr1 = dr.find_driver("DummyDriver")
        dr2 = dr.find_driver("PsutilDriver")
        dr3 = dr.find_driver("MemoryMeasureDriver")
        dr4 = dr.find_driver("MemoryStateDriver")

        dl = edr.find_emit_driver("LogEmitDriver")
        edv1 = dl.create_m_device()
        #edv1.enabled = True
        edv.create_new_emit_device(edv1)

        mdv1 = dr1.create_m_device()
        mdv1.driver.params[0].value = "5"
        mdv1.driver.params[1].value = "7.2"
        mdv1.driver.params[2].value = "0.4"
        control = aqt.MeasureEmitControl()
        control.decimals = 2
        #control.supressSameLimit = 0.5
        require = aqt.ValueRequire()
        require.warningAbove = 7.6
        require.alarmAbove = 7.8
        require.alarmConditions = []
        condition = aqt.Condition
        condition.description = "Not good"
        condition.condition = e.BinaryOpExpr(expr1=e.ObservableExpr(observableRef="1:A"), op=e.BinaryOp.LT, expr2=e.ValueExpr(6.4))
        require.alarmConditions.append(condition)
        cast(aqt.Measure, mdv1.observables[0]).emitControl = control
        cast(aqt.Measure, mdv1.observables[0]).require = require
        dv.create_new_device(mdv1)

        mdv2 = dr2.create_m_device()
        #mdv2.driver.params[0].value = "2"
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
        mdv3.driver.params[0].value = "15"
        mdv3.driver.params[1].value = "25"
        mdv3.driver.params[2].value = "0.9"
        dv.create_new_device(mdv3)

    await sleep(1)

    # await sleep(4)
    # d.observables['A'].pause()
    # await sleep(4)
    # d.observables['A'].unpause()
    # await sleep(4)
    # d.pause()
    # await sleep(4)
    # d.unpause()
    # await sleep(4)
