from .emitdevice import EmitDevice
from ..model import thing as aqt

emit_devices: dict[str, EmitDevice] = dict()


async def _add_emit_device(m_emit_device: aqt.EmitDevice) -> None:
    if not m_emit_device.enablement:
        m_emit_device.enablement = 'enabled'
    emit_device = EmitDevice()
    await emit_device.init(m_emit_device)
    emit_devices[emit_device.id] = emit_device
    if m_emit_device.enablement == 'enabled':
        await emit_device.start()


async def stop() -> None:
    for emit_device in emit_devices.values():
        if emit_device.m_emit_device.enablement == 'enabled':
            await emit_device.stop()


async def create_new_emit_device(m_emit_device: aqt.EmitDevice) -> str:
    assert not emit_devices.__contains__(m_emit_device.id)
    await _add_emit_device(m_emit_device)
    return m_emit_device.id
