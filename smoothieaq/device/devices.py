from typing import Optional

import aioreactive as rx
from aioreactive.subject import AsyncMultiSubject
from expression.collections import Seq, Map, Block

from ..driver.discover import discover as ds, discovers as dss
from ..model.globals import Globals
from ..model.thing import DriverRef
from ..modelobject import objectstore as os
from .device import Device, Observable
from ..div.emit import ObservableEmit, emit_empty
from ..model import thing as aqt
from ..util.rxutil import ix

devices: dict[str, Device] = dict()
device_paths: dict[str, str] = dict()
observables: dict[str, Observable] = dict()
rx_observables: dict[str, rx.AsyncObservable[ObservableEmit]] = dict()
discovers: dict[str, ds.Discover] = dict()

_rx_all_subject: rx.AsyncSubject[rx.AsyncObservable[ObservableEmit]] = rx.AsyncSubject()
rx_all_observables: AsyncMultiSubject[ObservableEmit] = AsyncMultiSubject()

_rx_device_updates: rx.AsyncSubject[aqt.Device] = rx.AsyncSubject()


async def init() -> None:
    _never_dispose = await rx.pipe(_rx_all_subject, rx.merge_inner()).subscribe_async(rx_all_observables)


def get_last_emit(observable_id: str) -> ObservableEmit:
    return emit_empty(observable_id)  # TODO

async def add_discovers() -> None:
    for driver in (await os.get(Globals, "globals")).discovers:
        await add_discover(driver)

async def add_discover(driver: DriverRef) -> None:
    discover = dss.get_discover(driver.id)
    discovers[driver.id] = discover
    params = Map.of_block(Block(driver.params or []).map(lambda p: (p.key, p.value)))
    discover.init(driver.path, "", driver.globalHal, params)
    await discover.start()

async def add_devices() -> None:
    for m_device in await os.get_all(aqt.Device):
        if not m_device.enablement == 'deleted':
            await _add_device(m_device)

async def _add_device(m_device: aqt.Device, start: bool = True) -> None:
    if not m_device.enablement:
        m_device.enablement = 'enabled'
    for m_observable in m_device.observables:
        if not m_observable.enablement:
            m_observable.enablement = 'enabled'
    device = Device()
    device.init(m_device)
    devices[m_device.id] = device
    if m_device.driver:
        device_paths[(m_device.driver.hal or m_device.driver.globalHal or "") + ":" + (m_device.driver.path or "")] = m_device.id
    if m_device.enablement == 'enabled' or m_device.enablement == 'discovered':
        rx_observables[device.status_id] = device.rx_status_observable
        for (id, observable) in device.observables.items():
            observables[observable.id] = observable
            rx_observables[observable.status_id] = observable.rx_status_observable
        await _rx_all_subject.asend(device.rx_all_observables)
        if device.m_device.enablement == 'enabled':
            for (id, observable) in device.observables.items():
                if observable.m_observable.enablement == 'enabled':
                    rx_observables[observable.id] = observable.rx_observable
            if start:
                await device.start()
    await _rx_device_updates.asend(m_device)

async def update_device(m_device: aqt.Device) -> None:
    old_device = get_device(m_device.id)
    assert not old_device.m_device.enablement == 'enabled' or old_device.paused # TODO nice exception
    if old_device.m_device.enablement == 'enabled' or old_device.m_device.enablement == 'discovered':
        del rx_observables[old_device.status_id]
        for (id, observable) in old_device.observables.items():
            del observables[observable.id]
            del rx_observables[observable.status_id]
            if old_device.m_device.enablement == 'enabled' and observable.m_observable.enabled == 'enabled':
                del rx_observables[observable.id]
    await _add_device(m_device, False)
    await os.replace(aqt.Device, m_device.id, m_device)


async def stop() -> None:
    for discover in discovers.values():
        await discover.stop()
    for device in devices.values():
        if device.m_device.enablement is not False:
            await device.stop()


async def create_new_device(m_device: aqt.Device) -> str:
    id = 1
    for k in list(devices.keys()):
        try:
            kid = int(k)
            if kid >= id:
                id = kid + 1
        except Exception:
            pass
    m_device.id = str(id)
    await _add_device(m_device)
    await os.put(aqt.Device, m_device.id, m_device)
    return m_device.id


def get_device(id: str) -> Device:
    return devices[id]


def get_observable(id: str) -> Observable:
    return observables[id]


def get_rx_observable(id: str) -> Optional[rx.AsyncObservable[ObservableEmit]]:
    if id[0] == '>':
        c = id.find(":")
        type = id[1:c-1]
        cid = id[c+1:len(id)-1]
        #print("!",type,cid)
        for d in devices.values():
            if d.m_device.type == type:
                return get_rx_observable(d.m_device.id + ':' + cid)
        from .observable import log
        log.error(f"Could not find {id}")
        raise KeyError(f"Could not find {id}")
    if not rx_observables.__contains__(id):
        return None
    return rx_observables[id]


def get_devices() -> Seq[aqt.Device]:
    return ix(devices.values())


def get_rx_device_updates() -> rx.AsyncObservable[aqt.Device]:
    #print (devices.values())
    return rx.pipe(  # todo, not really nice, may loose updates
        rx.from_iterable(ix(devices.values()).map(lambda d: d.m_device)),
        rx.concat(_rx_device_updates)
    )
