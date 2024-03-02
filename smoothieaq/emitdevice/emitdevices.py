from .emitdevice import EmitDevice
from ..model import thing as aqt

emit_devices: dict[str, EmitDevice] = dict()


def _add_emit_device(m_emit_device: aqt.EmitDevice) -> None:
    emit_device = EmitDevice()
    emit_device.init(m_emit_device)
    emit_devices[emit_device.id] = emit_device
    if m_emit_device.enabled is not False:
        emit_device.start()


def stop() -> None:
    for emit_device in emit_devices.values():
        if emit_device.m_emit_device.enabled is not False:
            emit_device.stop()


def create_new_emit_device(m_emit_device: aqt.EmitDevice) -> str:
    assert not emit_devices.__contains__(m_emit_device.id)
    _add_emit_device(m_emit_device)
    return m_emit_device.id
