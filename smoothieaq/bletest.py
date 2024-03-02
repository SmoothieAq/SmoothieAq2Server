from asyncio import sleep

from bleak import BleakScanner


async def bletest() -> None:

    devices = await BleakScanner.discover(timeout=5, return_adv=True)
    for key, value in devices.items():
        print(key, value)
        print(any(map(lambda su: su.upper() == "6E400001-B5A3-F393-E0A9-E50E24DCCA9E",value[1].service_uuids)))

    await sleep(5)



