import logging
import time
import asyncio
from dataclasses import dataclass
from typing import Optional

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak import BleakClient, BleakScanner
from datetime import datetime
import asyncio

from bleak.backends.service import BleakGATTService
from reactivex.abc import DisposableBase
from reactivex.scheduler.eventloop import AsyncIOScheduler

from . import commands
import reactivex as rx
from reactivex import operators as op

from ...util.rxutil import generator

log = logging.getLogger(__name__)


UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

msg_id = commands.next_message_id()

# This is inspired by https://github.com/TheMicDiet/chihiros-led-control/blob/main/chihirosctl.py
# Lots of credit should go to Michael Dietrich


@dataclass
class Command:
    cmd_id: int
    cmd_mode: int
    parameters: list[int]


class ChihirosCtl:

    def __init__(self, address: str, keep_connected_secs: float = 10.) -> None:
        self.address = address
        self.keep_connected_secs = keep_connected_secs
        self._command_subject: Optional[rx.Subject[Command]] = None
        self._command_disposable: Optional[DisposableBase] = None

    def start(self):
        self._command_subject = rx.Subject[Command]()
        self._command_disposable = rx.from_future(asyncio.get_event_loop().create_task(self._chihiros)).subscribe()

    def stop(self):
        self._command_subject.on_next(Command(cmd_id=-1, cmd_mode=-1, parameters=[]))
        self._command_subject.on_completed()
        self._command_subject = None

    async def _chihiros(self) -> None:

        def disconnected_callback(_: BleakClient):
            log.error(f"Unexpected BLE disconnect from {self.address}")

        client: BleakClient = BleakClient(self.address, disconnected_callback=disconnected_callback)
        last_time: float
        uart_service: BleakGATTService
        rx_characteristic: BleakGATTCharacteristic
        msg_id: tuple[bytes]

        try:
            gen = generator(self._command_subject.pipe(
                op.merge(rx.interval(self.keep_connected_secs)),
                op.subscribe_on(AsyncIOScheduler(asyncio.get_event_loop()))
            ))
            async for c in gen:
                if isinstance(c, Command):

                    if c.cmd_id == -1:  # stop signal
                        await gen.aclose()

                    if not client.is_connected:
                        await client.connect()
                        log.debug(f"Connected BLE to {self.address}")
                        uart_service = client.services.get_service(UART_SERVICE_UUID)
                        rx_characteristic = uart_service.get_characteristic(UART_RX_CHAR_UUID)
                        msg_id = commands.next_message_id()

                    last_time = time.time()
                    cmd = commands._create_command_encoding(c.cmd_id, c.cmd_mode, msg_id, c.parameters)
                    await client.write_gatt_char(rx_characteristic, cmd)
                    log.debug(f"BLE sent to {self.address}:", cmd.hex(":"))
                    msg_id = commands.next_message_id(msg_id)

                else:

                    if client.is_connected and last_time + self.keep_connected_secs < time.time():
                        await client.disconnect()
                        log.debug(f"disconnected BLE from {self.address}")

        except Exception as e:
            log.error(f"Error BLE on {self.address}", e)
        finally:
            if client.is_connected:
                await client.disconnect()

    def set_brightness(self, colorNo: int, brightness: int):
        self._command_subject.on_next(Command(cmd_id=90, cmd_mode=7, parameters=[colorNo, brightness]))

def list_devices(timeout: int = 5):
    discovered_devices = asyncio.run(BleakScanner.discover(timeout))
    for device in discovered_devices:
        print(device.name, device.address)


def set_brightness(device_address: str, colorNo: int, brightness: int):
    cmd = commands.create_manual_setting_command(msg_id, colorNo, brightness)
    asyncio.run(_execute_command(device_address, cmd))


def set_rgb_brightness(device_address: str, brightness: tuple[int, int, int]):
    global msg_id
    cmds = []
    for c, b in enumerate(brightness):
        cmds.append(commands.create_manual_setting_command(msg_id, c, b))
        msg_id = commands.next_message_id(msg_id)
    asyncio.run(_execute_command(device_address, *cmds))


def add_setting(device_address: str,
                sunrise: datetime,
                sunset: datetime,
                max_brightness: int = 100,
                ramp_up_in_minutes: int = 0,
                weekdays: int = 127):
    cmd = commands.create_add_auto_setting_command(msg_id, sunrise.time(), sunset.time(), (max_brightness, 255, 255),
                                                   ramp_up_in_minutes, weekdays)
    asyncio.run(_execute_command(device_address, cmd))


def add_rgb_setting(device_address: str,
                    sunrise: datetime,
                    sunset: datetime,
                    max_brightness: tuple[int, int, int] = (100, 100, 100),
                    ramp_up_in_minutes: int = 0,
                    weekdays: int = 127):
    cmd = commands.create_add_auto_setting_command(msg_id, sunrise.time(), sunset.time(), max_brightness,
                                                   ramp_up_in_minutes, weekdays)
    asyncio.run(_execute_command(device_address, cmd))


def remove_setting(device_address: str,
                   sunrise: datetime,
                   sunset: datetime,
                   ramp_up_in_minutes: int = 0,
                   weekdays: int = 127):
    cmd = commands.create_delete_auto_setting_command(msg_id, sunrise.time(), sunset.time(),
                                                      ramp_up_in_minutes, weekdays)
    asyncio.run(_execute_command(device_address, cmd))


def reset_settings(device_address: str):
    cmd = commands.create_reset_auto_settings_command(msg_id)
    asyncio.run(_execute_command(device_address, cmd))


def enable_auto_mode(device_address: str):
    global msg_id
    switch_cmd = commands.create_switch_to_auto_mode_command(msg_id)
    msg_id = commands.next_message_id(msg_id)
    time_cmd = commands.create_set_time_command(msg_id)
    asyncio.run(_execute_command(device_address, switch_cmd, time_cmd))


def handle_disconnect(_: BleakClient):
    print("Device was disconnected")
    # cancelling all tasks effectively ends the program
#    for task in asyncio.all_tasks():
#        task.cancel()


def handle_notifications(sender: BleakGATTCharacteristic, data: bytearray):
    print("Received from sender:", sender, "data:", data.hex(" "))
    if data:
        if data[0] == 91 and data[5] == 10:
            device_time = (((data[6] & 255) * 256) + (data[7] & 255)) * 60
            print("Current device time:", device_time)
        firmware_version = data[1]
        print("Current firmware version", firmware_version)


async def _execute_command(device_address: str, *commands: bytearray):
    async with BleakClient(device_address, disconnected_callback=handle_disconnect) as client:
        print("Connected to device:", device_address)

        # await client.start_notify(UART_TX_CHAR_UUID, handle_notifications)
        # print("Subscribed for notifications")
        uart_service = client.services.get_service(UART_SERVICE_UUID)
        rx_characteristic = uart_service.get_characteristic(UART_RX_CHAR_UUID)
        for command in commands:
            await client.write_gatt_char(rx_characteristic, command)
            print("Sent command", command.hex(":"))

