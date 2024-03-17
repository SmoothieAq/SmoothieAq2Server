import logging
from dataclasses import dataclass
from typing import Optional

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTService
from expression.collections import Map

from smoothieaq.hal.chihiros import commands
from smoothieaq.hal.connecthal import AbstractCommand, ConnectHal, _HalConnection

log = logging.getLogger(__name__)

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

msg_id = commands.next_message_id()


# This is inspired by https://github.com/TheMicDiet/chihiros-led-control/blob/main/chihirosctl.py
# Lots of credit should go to Michael Dietrich


@dataclass
class Command(AbstractCommand):
    cmd_id: int
    cmd_mode: int
    parameters: list[int]


class ChihirosHal(ConnectHal[Command]):

    def create_hal_connection(self) -> '_HalConnection[Command, ConnectHal]':
        return _Chihiros(self)


class _Chihiros(_HalConnection[Command, ChihirosHal]):

    def __init__(self, connectHal: ChihirosHal):
        super().__init__(connectHal)
        self.client: BleakClient = BleakClient(connectHal.path, disconnected_callback=self.disconnected_callback)
        self.uart_service: BleakGATTService
        self.rx_characteristic: BleakGATTCharacteristic
        self.msg_id: tuple[bytes] = commands.next_message_id()

    def disconnected_callback(self, _: BleakClient):
        if not self.disconnecting:
            log.error(f"Unexpected BLE disconnect from {self.connectHal.path}")

    async def do_connect(self):
        await self.client.connect()
        log.debug(f"Connected BLE to {self.connectHal.path}")
        self.uart_service = self.client.services.get_service(UART_SERVICE_UUID)
        self.rx_characteristic = self.uart_service.get_characteristic(UART_RX_CHAR_UUID)
        self.msg_id = commands.next_message_id()

    async def do_disconnect(self):
        await self.client.disconnect()
        log.debug(f"disconnected BLE from {self.connectHal.path}")

    async def do_command(self, command: Command):
        await super().do_command(command)
        cmd = commands._create_command_encoding(command.cmd_id, command.cmd_mode, self.msg_id, command.parameters)
        await self.client.write_gatt_char(self.rx_characteristic, cmd)
        log.debug(f"BLE sent to {self.connectHal.path}: {cmd.hex(":")}")
        self.msg_id = commands.next_message_id(self.msg_id)
