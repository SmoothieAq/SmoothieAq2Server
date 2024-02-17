from smoothieaq.div.emit import *
from .device import *
from ..model import thing as aqt

devices: dict[str, Device] = dict()
observables: dict[str, Observable] = dict()
rx_observables: dict[str, rx.Observable[ObservableEmit]] = dict()

_rx_all_subject: rx.Subject[rx.Observable[ObservableEmit]] = rx.Subject()
rx_all_observables: rx.Observable[ObservableEmit] = _rx_all_subject.pipe(op.merge_all())


def _add_device(m_device: aqt.Device) -> None:
    device = Device()
    device.init(m_device)
    devices[m_device.id] = device
    rx_observables[device.status_id] = device.rx_status_observable
    for (id, observable) in device.observables.items():
        observables[observable.id] = observable
        rx_observables[observable.id] = observable.rx_observable
        rx_observables[observable.status_id] = observable.rx_status_observable
    _rx_all_subject.on_next(device.rx_all_observables)
    device.start()


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


def get_rx_observable(id: str) -> rx.Observable[ObservableEmit]:
    return rx_observables[id]
