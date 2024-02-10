# This is a sample Python script.
import asyncio

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from smoothieaq.enumtest import *
from smoothieaq.rxtest import *
from smoothieaq.devtest import *


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}', float(True), float(False))  # Press ⌘F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # print(enum_test())
    #asyncio.run(rxtest())
    asyncio.run(test())
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
