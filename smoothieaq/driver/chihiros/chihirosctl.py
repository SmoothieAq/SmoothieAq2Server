import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

import aioreactive as rx
from aioreactive.create import interval
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTService

from . import commands

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
        self._command_subject: Optional[rx.AsyncSingleSubject[Command | int]] = None
        self._command_disposable: Optional[rx.AsyncDisposable] = None

    def _ctl(self) -> Callable[[Command | int], Awaitable[None]]:
        chihiros = _Chihiros(self)

        async def _(c: Command | int) -> None:
            match c:
                case Command(cmd_id=-1):
                    await chihiros.disconnect()
                case Command():
                    await chihiros.do_command(c)
                case _:
                    await chihiros.disconnect_if_timeout()

        return _

    async def start(self):
        self._command_subject = rx.AsyncSubject[Command | int]()
        self._command_disposable = await rx.pipe(
            self._command_subject,
            rx.merge(interval(self.keep_connected_secs, self.keep_connected_secs))
        ).subscribe_async(self._ctl())

    async def stop(self):
        await self._command_subject.asend(Command(cmd_id=-1, cmd_mode=-1, parameters=[]))
        await self._command_subject.aclose()
        self._command_subject = None
        await self._command_disposable.dispose_async()

    async def set_brightness(self, colorNo: int, brightness: int):
        await self._command_subject.asend(Command(cmd_id=90, cmd_mode=7, parameters=[colorNo, brightness]))


class _Chihiros:

    def __init__(self, ctl: ChihirosCtl):
        self.ctl = ctl
        self.client: BleakClient = BleakClient(ctl.address, disconnected_callback=self.disconnected_callback)
        self.last_time: float = 0
        self.uart_service: BleakGATTService
        self.rx_characteristic: BleakGATTCharacteristic
        self.msg_id: tuple[bytes] = commands.next_message_id()
        self.disconnecting = False

    def disconnected_callback(self, _: BleakClient):
        if not self.disconnecting:
            log.error(f"Unexpected BLE disconnect from {self.ctl.address}")

    async def connect(self):
        if not self.client.is_connected:
            self.disconnecting = False
            await self.client.connect()
            log.debug(f"Connected BLE to {self.ctl.address}")
            self.uart_service = self.client.services.get_service(UART_SERVICE_UUID)
            self.rx_characteristic = self.uart_service.get_characteristic(UART_RX_CHAR_UUID)
            self.msg_id = commands.next_message_id()

    async def disconnect(self):
        if self.client.is_connected:
            self.disconnecting = True
            await self.client.disconnect()
            log.debug(f"disconnected BLE from {self.ctl.address}")

    async def disconnect_if_timeout(self):
        if self.client.is_connected and self.last_time + self.ctl.keep_connected_secs < time.time():
            await self.disconnect()

    async def do_command(self, command: Command):
        if not self.client.is_connected:
            await self.connect()
        self.last_time = time.time()
        cmd = commands._create_command_encoding(command.cmd_id, command.cmd_mode, self.msg_id, command.parameters)
        await self.client.write_gatt_char(self.rx_characteristic, cmd)
        log.debug(f"BLE sent to {self.ctl.address}: {cmd.hex(":")}")
        self.msg_id = commands.next_message_id(self.msg_id)

# def list_devices(timeout: int = 5):
#     discovered_devices = asyncio.run(BleakScanner.discover(timeout))
#     for device in discovered_devices:
#         print(device.name, device.address)
#
#
# def set_brightness(device_address: str, colorNo: int, brightness: int):
#     cmd = commands.create_manual_setting_command(msg_id, colorNo, brightness)
#     asyncio.run(_execute_command(device_address, cmd))
#
#
# def set_rgb_brightness(device_address: str, brightness: tuple[int, int, int]):
#     global msg_id
#     cmds = []
#     for c, b in enumerate(brightness):
#         cmds.append(commands.create_manual_setting_command(msg_id, c, b))
#         msg_id = commands.next_message_id(msg_id)
#     asyncio.run(_execute_command(device_address, *cmds))
#
#
# def add_setting(device_address: str,
#                 sunrise: datetime,
#                 sunset: datetime,
#                 max_brightness: int = 100,
#                 ramp_up_in_minutes: int = 0,
#                 weekdays: int = 127):
#     cmd = commands.create_add_auto_setting_command(msg_id, sunrise.time(), sunset.time(), (max_brightness, 255, 255),
#                                                    ramp_up_in_minutes, weekdays)
#     asyncio.run(_execute_command(device_address, cmd))
#
#
# def add_rgb_setting(device_address: str,
#                     sunrise: datetime,
#                     sunset: datetime,
#                     max_brightness: tuple[int, int, int] = (100, 100, 100),
#                     ramp_up_in_minutes: int = 0,
#                     weekdays: int = 127):
#     cmd = commands.create_add_auto_setting_command(msg_id, sunrise.time(), sunset.time(), max_brightness,
#                                                    ramp_up_in_minutes, weekdays)
#     asyncio.run(_execute_command(device_address, cmd))
#
#
# def remove_setting(device_address: str,
#                    sunrise: datetime,
#                    sunset: datetime,
#                    ramp_up_in_minutes: int = 0,
#                    weekdays: int = 127):
#     cmd = commands.create_delete_auto_setting_command(msg_id, sunrise.time(), sunset.time(),
#                                                       ramp_up_in_minutes, weekdays)
#     asyncio.run(_execute_command(device_address, cmd))
#
#
# def reset_settings(device_address: str):
#     cmd = commands.create_reset_auto_settings_command(msg_id)
#     asyncio.run(_execute_command(device_address, cmd))
#
#
# def enable_auto_mode(device_address: str):
#     global msg_id
#     switch_cmd = commands.create_switch_to_auto_mode_command(msg_id)
#     msg_id = commands.next_message_id(msg_id)
#     time_cmd = commands.create_set_time_command(msg_id)
#     asyncio.run(_execute_command(device_address, switch_cmd, time_cmd))
#
#
# def handle_disconnect(_: BleakClient):
#     print("Device was disconnected")
#     # cancelling all tasks effectively ends the program
# #    for task in asyncio.all_tasks():
# #        task.cancel()
#
#
# def handle_notifications(sender: BleakGATTCharacteristic, data: bytearray):
#     print("Received from sender:", sender, "data:", data.hex(" "))
#     if data:
#         if data[0] == 91 and data[5] == 10:
#             device_time = (((data[6] & 255) * 256) + (data[7] & 255)) * 60
#             print("Current device time:", device_time)
#         firmware_version = data[1]
#         print("Current firmware version", firmware_version)
#
#
# async def _execute_command(device_address: str, *commands: bytearray):
#     async with BleakClient(device_address, disconnected_callback=handle_disconnect) as client:
#         print("Connected to device:", device_address)
#
#         # await client.start_notify(UART_TX_CHAR_UUID, handle_notifications)
#         # print("Subscribed for notifications")
#         uart_service = client.services.get_service(UART_SERVICE_UUID)
#         rx_characteristic = uart_service.get_characteristic(UART_RX_CHAR_UUID)
#         for command in commands:
#             await client.write_gatt_char(rx_characteristic, command)
#             print("Sent command", command.hex(":"))
#
