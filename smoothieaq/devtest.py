import datetime
from asyncio import sleep
from typing import cast

import smoothieaq.model.expression as ex
import smoothieaq.model.step as st
from smoothieaq.device import devices as dv
from smoothieaq.device.device import *
from smoothieaq.driver import drivers as dr
from .driver.drivers import create_m_device
from .emitdriver import emitdrivers as edr
from .emitdevice import emitdevices as edv
from smoothieaq.div import time
import time as t


async def test():

    #time.simulate(start_time=datetime.time(8,25), speed=60, minDuration=0.5)
    #time.simulate(start_time=datetime.time(8,25), speed=5, minDuration=0.5)

    async def p(e):
        print(
            f"{e.observable_id}: {e.value or ''} {e.enumValue or ''} {e.note or ''} ({t.strftime('%Y/%m/%d %H:%M:%S', t.localtime(e.stamp))}) {e.stamp}"
        )
    async def e(ex):
        print("error", ex)
    await dv.rx_all_observables.subscribe_async(p,e)

    await dv.create_new_device(create_m_device(await dr.get_m_driver("TimeDriver")))

    await sleep(5)
    #await cast(Amount, dv.get_observable("1:R2")).set_value(0.)
    #await cast(Amount, dv.get_observable("1:G2")).set_value(5.)
    #await sleep(100)

    if False:
        sl = await edr.find_emit_driver("MariadbEmitDriver")
        slv1 = sl.create_m_device()
        #slv1.enabled = True
        await edv.create_new_emit_device(slv1)
        await sleep(1)

    if False:
        mqttd = await dr.get_m_driver("HomeAssistantMqttDriver")
        mqttm = create_m_device(mqttd)
        await dv.create_new_device(mqttm)
        #await sleep(4)
        #print("-->!!")
        #await cast(State, dv.get_observable("4:D")).set_value("true")
        await sleep(1)

    if False:
        drch = await dr.get_m_driver("Chihiros2LedDriver")
        mdvch = create_m_device(drch, aqt.DriverRef(path="C21C06F8-D0E0-DC60-7D78-D8BBFCF23DAD"))
        dvch = await dv.create_new_device(mdvch)

        await cast(Amount, dv.get_observable(dvch + ":A4")).reset()
        await cast(Amount, dv.get_observable(dvch + ":A2")).set_value(1200.)

        await sleep(1)

        await cast(Amount, dv.get_observable(dvch + ":R2")).set_value(0.)
        await cast(Amount, dv.get_observable(dvch + ":G2")).set_value(0.)

        #for i in range(0,100):
        #    await cast(Amount, dv.get_observable(dvch + ":R2")).set_value(float(i))
        #    await cast(Amount, dv.get_observable(dvch + ":G2")).set_value(float(i))
        #    await sleep(0.5)

        await sleep(4)

    if False:
        dr1 = await dr.get_m_driver("DummyDriver")
        dr2 = await dr.get_m_driver("PsutilDriver")
        dr3 = await dr.get_m_driver("MemoryMeasureDriver")
        dr4 = await dr.get_m_driver("MemoryStateDriver")

    if False:
        dl = await edr.find_emit_driver("LogEmitDriver")
        edv1 = dl.create_m_device()
        #edv1.enabled = True
        await edv.create_new_emit_device(edv1)
        await sleep(1)

    if False:
        mdv1 = create_m_device(dr1)
        mdv1.driver.params[0].value = "30"
        mdv1.driver.params[1].value = "7.2"
        mdv1.driver.params[2].value = "0.4"
        control = aqt.MeasureEmitControl()
        control.decimals = 2
        #control.supressSameLimit = 0.5
        require = aqt.ValueRequire()
        require.warningAbove = 7.6
        require.alarmAbove = 7.8
        require.alarmConditions = []
        condition = aqt.Condition()
        condition.description = "Not good"
        condition.condition = ex.BinaryOpExpr(expr1=ex.ObservableExpr(observableRef="1:A"), op=ex.BinaryOp.LT, expr2=ex.ValueExpr(6.8))
        require.alarmConditions.append(condition)
        cast(aqt.Measure, mdv1.observables[0]).emitControl = control
        cast(aqt.Measure, mdv1.observables[0]).require = require
        action = aqt.Action(id='X1', steps=[st.WaitStep(id='wait', timeToWait=3), st.PollStep(id='poll', observableRef='1')])
        mdv1.observables.append(action)
        chore = aqt.Chore(id='C1', steps=[st.WaitStep(id='wait', timeToWait=1), st.DoneStep(id='done')])
        mdv1.observables.append(chore)
        ecid = await dv.create_new_device(mdv1)

        await sleep(3)
        #await dv.observables[ecid+':C1'].async_do_action()
        #await dv.observables[ecid+':C1'].skip()
        #await dv.observables[ecid+':C1'].delay()
        #await dv.observables[ecid+':C1'].done()
        await dv.observables[ecid+':C1'].start_chore()
        await sleep(2)
        await dv.observables[ecid+':C1'].input('done', RawEmit())

        #await sleep(9)

    if False:
        mdv2 = create_m_device(dr2)
        #mdv2.driver.params[0].value = "2"
        await dv.create_new_device(mdv2)

        mdv4 = create_m_device(dr3)
        id4 = await dv.create_new_device(mdv4)

        mdv5 = create_m_device(dr4)
        cast(aqt.State,mdv5.observables[0]).setExpr = ex.RxOp1Expr(ex.RxOp1.DEBOUNCE,3,ex.RxOp0Expr(ex.RxOp0.DISTINCT,ex.IfExpr(
            ifExpr=ex.BinaryOpExpr(expr1=ex.ObservableExpr(observableRef="1:A"),op=ex.BinaryOp.GT,expr2=ex.ValueExpr(7.3)),
            thenExpr=ex.EnumValueExpr("on"),
            elseExpr=ex.EnumValueExpr("off")
        )))
        await dv.create_new_device(mdv5)

        await sleep(10)
        await cast(Measure, dv.get_observable(id4+":A")).measurement(99)

        mdv3 = create_m_device(dr1)
        mdv3.driver.params[0].value = "15"
        mdv3.driver.params[1].value = "25"
        mdv3.driver.params[2].value = "0.9"
        await dv.create_new_device(mdv3)

    #await sleep(200)

    # await sleep(4)
    # d.observables['A'].pause()
    # await sleep(4)
    # d.observables['A'].unpause()
    # await sleep(4)
    # d.pause()
    # await sleep(4)
    # d.unpause()
    # await sleep(4)
