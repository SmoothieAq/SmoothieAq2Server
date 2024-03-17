# This is a sample Python script.
import asyncio

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from smoothieaq.enumtest import *
from smoothieaq.rxtest import *
from smoothieaq.devtest import *
from smoothieaq.bletest import *
from smoothieaq.div import objectstore as os, time as t
import logging


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}', float(True), float(False))  # Press ⌘F8 to toggle the breakpoint.


async def doit():
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("smoothieaq").setLevel(logging.INFO)
    logging.getLogger("smoothieaq.hal").setLevel(logging.DEBUG)
    logging.getLogger("smoothieaq.driver.driver").setLevel(logging.INFO)
    logging.info("info")
    await os.load()
    await sleep(1)
    #t.simulate(speed=10)
    await test()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # print(enum_test())
    #asyncio.run(rxtest())
    asyncio.run(doit())
    #asyncio.run(bletest())
#    from smoothieaq.util.rxutil import _distinct_until_changed_test
#    asyncio.run(_distinct_until_changed_test())
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
