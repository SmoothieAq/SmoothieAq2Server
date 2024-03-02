from typing import Optional

from .device import Device, Observable
from ..div.emit import ObservableEmit, emit_empty
import reactivex as rx
import reactivex.operators as op
from ..model import thing as aqt

devices: dict[str, Device] = dict()
observables: dict[str, Observable] = dict()
rx_observables: dict[str, rx.Observable[ObservableEmit]] = dict()

_rx_all_subject: rx.Subject[rx.Observable[ObservableEmit]] = rx.Subject()
rx_all_observables: rx.Observable[ObservableEmit] = _rx_all_subject.pipe(op.merge_all())

_rx_device_updates: rx.Subject[aqt.Device] = rx.Subject()


def get_last_emit(observable_id: str) -> ObservableEmit:
    return emit_empty(observable_id)  # TODO


def _add_device(m_device: aqt.Device) -> None:
    device = Device()
    device.init(m_device)
    devices[m_device.id] = device
    rx_observables[device.status_id] = device.rx_status_observable
    for (id, observable) in device.observables.items():
        observables[observable.id] = observable
        rx_observables[observable.status_id] = observable.rx_status_observable
    _rx_all_subject.on_next(device.rx_all_observables)
    if device.m_device.enabled is not False:
        for (id, observable) in device.observables.items():
            if observable.m_observable.enabled is not False:
                rx_observables[observable.id] = observable.rx_observable
        device.start()
    _rx_device_updates.on_next(m_device)


def stop() -> None:
    for device in devices.values():
        if device.m_device.enabled is not False:
            device.stop()


def create_new_device(m_device: aqt.Device) -> str:
    id = 1
    for k in list(devices.keys()):
        try:
            kid = int(k)
            if kid >= id:
                id = kid + 1
        except Exception:
            pass
    m_device.id = str(id)
    _add_device(m_device)
    return m_device.id


def get_device(id: str) -> Device:
    return devices[id]


def get_observable(id: str) -> Observable:
    return observables[id]


def get_rx_observable(id: str) -> Optional[rx.Observable[ObservableEmit]]:
    if id[0] == '>':
        c = id.find(":")
        type = id[1:c-1]
        cid = id[c+1:len(id)-1]
        print("!",type,cid)
        for d in devices.values():
            if d.m_device.type == type:
                return get_rx_observable(d.m_device.id + ':' + cid)
        from .device import log
        log.error(f"Could not find {id}")
        raise Exception(f"Could not find {id}")
    if not rx_observables.__contains__(id):
        return None
    return rx_observables[id]


def get_rx_device_updates() -> rx.Observable[aqt.Device]:
    return rx.concat(
        rx.from_list(list(map(lambda d: d.m_device, devices.values()))),
        _rx_device_updates
    )
