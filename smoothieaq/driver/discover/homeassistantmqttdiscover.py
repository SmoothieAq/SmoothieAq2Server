import logging
import re
from typing import cast, Optional

import aioreactive as rx
from expression.collections import Map

from .discover import Discover
from ..driver import Driver
from ...device import devices
from ...device.devices import create_new_device
from ...hal.globals import globalhals
from ...hal.globals.mqtthal import MqttHal
from ...model.thing import Device, DriverRef, Measure, Observable, Param, MeasureEmitControl, State, Event
from ...util.rxutil import AsyncBehaviorSubject

log = logging.getLogger(__name__)


def _new_measure(type: str, d: dict) -> (str, Measure):
    types = {'temperature': 'temp'}
    units = {}
    measure = Measure()
    if d.get('device_class') in types:
        measure.quantityType = types[d.get('device_class')]
    else:
        measure.quantityType = d.get('device_class')
    if d.get('unit_of_measurement') in units:
        measure.unit = units[d.get('unit_of_measurement')]
    else:
        measure.unit = d.get('unit_of_measurement')
    return ('F:R::', measure)


def _new_state(type: str, d: dict) -> (str, State):
    state = State()
    if type == 'binary_sensor':
        state.enumType = 'boolean'
        return (f"B:R:{d.get('payload_on')}/{d.get('payload_off')}:", state)
    if type == 'switch':
        state.enumType = 'boolean'
        if d.get('command_topic'):
            state.operations = ["set"]
        return (f"B:W:{d.get('payload_on')}/{d.get('payload_off')}:{d.get('command_topic')}", state)
    if type == 'select':
        state.description = str(d.get('options'))
        if d.get('command_topic'):
            state.operations = ["set"]
        return (f"S:W:{'/'.join(d.get('options'))}:{d.get('command_topic')}", state)
    raise KeyError


def _new_event(type: str, d: dict) -> (str, Event):
    event = Event()
    if d.get('command_topic'):
        event.operations = ["set"]
    return (f"E:W::{d.get('command_topic')}", event)


class HomeAssistantMqttDiscover(Discover[MqttHal]):
    id = "HomeAssistantMqttDiscover"

    def __init__(self):
        super().__init__()
        self._rx_mqtt: AsyncBehaviorSubject[dict] = AsyncBehaviorSubject({})
        self._disposables: list[rx.AsyncDisposable] = []
        self._device_paths_in_progress: dict[str, dict[str, dict]] = {}

    def init(self, path: str, hal: str, globalHal: str, params: Map[str, str]) -> 'Driver':
        log.info(f"doing discover.init({self.id}/{path})")
        self.path = path
        self.params = params
        self.is_global_hal = True
        self.global_hal = globalHal
        self.hal = cast(MqttHal, globalhals.get_global_hal(globalHal))
        return self

    async def _new_device(self, device_path: str):
        try:
            d = self._device_paths_in_progress[device_path]
            del self._device_paths_in_progress[device_path]

            fst = d[next(iter(d))]
            dev = fst['device']
            device = Device()
            device.name = dev.get('name')
            if device.name == "Zigbee2MQTT Bridge":
                device.enablement = 'ignored'
            device.description = dev.get('manufacturer') + ' ' + dev.get('model')
            device.make = dev.get('manufacturer') + ' ' + dev.get('model')
            device.driver = DriverRef()
            device.driver.id  = "HomeAssistantMqttDriver"
            device.driver.path = fst['state_topic']
            device.driver.globalHal = self.global_hal
            device.driver.params = []
            device.observables = []

            m = re.compile(r"\.(\w*)")

            next_letter = ['A']
            def add_obs(name: str, d: dict, pv: str, observable: Observable):
                observable.id = next_letter[0]
                observable.name = d.get('name') or name
                try:
                    mo = m.search(d.get('value_template'))
                    mk = mo.group(1)
                except:
                    mk = name
                next_letter[0] = chr(ord(next_letter[0])+1)
                device.driver.params.append(Param(key = mk, value = f"{observable.id}:{pv}"))
                device.observables.append(observable)

            for k in d.keys():
                obs = d[k]
                topic_elements = obs["_topic"].split('/')
                type = topic_elements[1]
                if type == 'sensor':
                    if not obs.get('device_class') == 'timestamp':
                        add_obs(k, obs, *_new_measure(type, obs))
                elif type == 'binary_sensor' or type == 'switch' or type == 'select':
                    add_obs(k, obs, *_new_state(type, obs))
                elif type == 'button':
                    add_obs(k, obs, *_new_event(type, obs))
                else:
                    log.warning(f"unknown type {type} on {device_path} {k}")

            id = await create_new_device(device)
            log.info(f"created new device {id} {device.name} {device.description}")
        except Exception as e:
            log.error(f"{device_path}", exc_info=e)

    async def _on_message(self, d: dict):
        if not d: return
        topic_elements = d["_topic"].split('/')
        path = topic_elements[2]
        device_path = self.global_hal + ':' + path
        if device_path in devices.device_paths:
            return
        if not device_path in self._device_paths_in_progress:
            self._device_paths_in_progress[device_path] = {}
            disposable: Optional[rx.AsyncDisposable] = None
            async def _do_device(n: int):
                await disposable.dispose_async()
                await self._new_device(device_path)
            disposable = await rx.interval(1.0,1).subscribe_async(_do_device)
        d["_type"] = topic_elements[1]
        self._device_paths_in_progress[device_path][topic_elements[3]] = d

    async def start(self) -> None:
        await super().start()
        self._disposables.append( await self._rx_mqtt.subscribe_async(self._on_message))
        await self.hal.subscribe("homeassistant/+/+/+/config", self._rx_mqtt)

    async def stop(self):
        await self.hal.unsubscribe("homeassistant/+/+/+/config")
        for d in self._disposables:
            await d.dispose_async()
        await super().stop()