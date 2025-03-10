import logging
from sys import float_repr_style
from typing import Optional, cast

import bleak

from .btdiscover import BtDiscover
from ..drivers import get_m_driver, create_m_device
from ...model.expression import BinaryOpExpr, ObservableExpr, ValueExpr, BinaryOp, ConvertExpr, Expr
from ...model.thing import Device, DriverRef, Amount

log = logging.getLogger(__name__)

# Largely based on information from: https://github.com/TheMicDiet/chihiros-led-control/blob/main/custom_components/chihiros/chihiros_led_control/device/__init__.py
_known_models: dict[str: (str,str,str,list[float],Optional[int],Optional[str])] = {
    'DYDD': ("Tiny Terrarium Egg", "R:G", "CC3388:33CC88", 550, None),
    'MDTM': ("Magnetic Light", "R:G", "CC3388:33CC88", 1200, None),
    'DYNA2': ("A II", "W", "FFFFFF", 999,
              "AII301: 1628, AII351: 1699, AII361: 1699, AII401: 1699, AII451: 1957, AII501: 2063, AII601: 2450, AII801: 3300, AII901: 3580, AII1201: 4800"),
    'DYNA2N': ("A II", "W", "FFFFFF", 999, # perhaps a A II Max? then the max lumen is different
              "AII301: 1628, AII351: 1699, AII361: 1699, AII401: 1699, AII451: 1957, AII501: 2063, AII601: 2450, AII801: 3300, AII901: 3580, AII1201: 4800"),
    'DYNC2N': ("C II", "W", "FFFFFF", 1500, None),
    'DYNCRGP': ("C II RGB", "R:G:B", "AA2233:33AA22:2233AA", 1580, None),
    'DYCOM': ("Commander 1", "W:R:G:B", "888888:880000:880000:880000", 999, "According to you LED light"),
    'DYLED': ("Commander 4", "R:G:B", "AA2233:33AA22:2233AA", 999, "According to you LED light"),
    'DYU550': ("Universal WRGB", "R:G:B:W", "880000:880000:880000:888888", 999, "Unknown"),
    'DYU600': ("Universal WRGB", "R:G:B:W", "880000:880000:880000:888888", 999, "Unknown"),
    'DYU700': ("Universal WRGB", "R:G:B:W", "880000:880000:880000:888888", 999, "Unknown"),
    'DYU800': ("Universal WRGB", "R:G:B:W", "880000:880000:880000:888888", 999, "Unknown"),
    'DYU920': ("Universal WRGB", "R:G:B:W", "880000:880000:880000:888888", 999, "Unknown"),
    'DYU1000': ("Universal WRGB", "R:G:B:W", "880000:880000:880000:888888", 999, "Unknown"),
    'DYU1200': ("Universal WRGB", "R:G:B:W", "880000:880000:880000:888888", 999, "Unknown"),
    'DYU1500': ("Universal WRGB", "R:G:B:W", "880000:880000:880000:888888", 999, "Unknown"),
    'DYNWRGB': ("WRGB II", "R:G:B", "AA2233:33AA22:2233AA", None, "Unknown"),
    'DYNW30': ("WRGB II 30", "R:G:B", "AA2233:33AA22:2233AA", 3000, "10th ed: 3000, old: 2300"),
    'DYNW45': ("WRGB II 45", "R:G:B", "AA2233:33AA22:2233AA", 4700, "10th ed: 4700, old: 3600"),
    'DYNW60': ("WRGB II 60", "R:G:B", "AA2233:33AA22:2233AA", 5900, "10th ed: 5900, old: 4500"),
    'DYNW90': ("WRGB II 90", "R:G:B", "AA2233:33AA22:2233AA", 8400, "10th ed: 8400, old: 6200"),
    'DYNW120': ("WRGB II 120", "R:G:B", "AA2233:33AA22:2233AA", 11000, "10th ed: 11000, old: 7700"),
    'DYWPRO30': ("WRGB II Pro 30", "R:G:B:W", "880000:880000:880000:888888", 3260, None),
    'DYWPRO45': ("WRGB II Pro 45", "R:G:B:W", "880000:880000:880000:888888", 5000, None),
    'DYWPRO60': ("WRGB II Pro 60", "R:G:B:W", "880000:880000:880000:888888", 6630, None),
    'DYWPRO80': ("WRGB II Pro 60", "R:G:B:W", "880000:880000:880000:888888", 8170, None),
    'DYWPRO90': ("WRGB II Pro 90", "R:G:B:W", "880000:880000:880000:888888", 9250, None),
    'DYWPR120': ("WRGB II Pro 120", "R:G:B:W", "880000:880000:880000:888888", 11170, None),
    'DYSILN': ("WRGB II Slim", "R:G:B", "AA2233:33AA22:2233AA", None, "SLIM30: 1200, SLIM45: 1800, SLIM60: 2400, SLIM90: 3600, SLIM120: 4800"),
}
_default_model = 'DYLED'

class ChihirosDiscover(BtDiscover):
    id = "ChihirosDiscover"

    async def _new_bt_device(self, path: str, dev: bleak.BLEDevice, data: bleak.AdvertisementData)-> Optional[Device]:
        (make, color_ids, colors, lum, lum_text) = _known_models.get(dev.name[:-12], _known_models[_default_model])

        device = create_m_device(await get_m_driver("LedDriver"))
        device.name = f"Chihiros {make}"
        device.description = f"Chihiros {make} LED light"
        if lum_text:
            device.description += f" - you should set A2/maxLume to: {lum_text}"
        device.make = f"Chihiros {make}"
        device.driver.hal = "ChihirosLedHal"
        device.driver.path = path
        device.driver.params[0].value = color_ids
        device.driver.params[1].value = colors

        # subjective brightness: https://computergraphics.stackexchange.com/questions/5085/light-intensity-of-an-rgb-value
        subjective = [0.21, 0.72, 0.07]
        color_id = color_ids.split(":")
        color = colors.split(":")
        color_elm = [[int(col[0:2], 16), int(col[2:4], 16), int(col[4:6], 16)] for col in color]
        tot_elm = [sum([cl[i] for cl in color_elm]) for i in range(3)]
        weight = [sum([cl[i] / tot_elm[i] * subjective[i] for i in range(3)]) for cl in color_elm]

        for i in range(len(color_id)):
            id = color_id[i]

            c1 = Amount()
            device.observables.append(c1)
            c1.id = id+"1"
            c1.name = f"Max lumen {id}"
            c1.description = f"Maximum lumen for {id} color leds"
            c1.quantityType = 'luminousFlux'
            c1.unit = 'lm'
            c1.category = 'internal'
            c1.expr = BinaryOpExpr(op = BinaryOp.MULTIPLY, expr1=ObservableExpr('A2'), expr2=ValueExpr(weight[i]))
            c1.precision = 1.0

            c2 = Amount()
            device.observables.append(c2)
            c2.id = id + "2"
            c2.name = f"Brightness {id}"
            c1.description = f"Brightness for {id} color leds"
            c1.quantityType = 'fraction'
            c1.unit = '%'
            c1.category = 'internal'
            c1.operations = ['set']

            c3 = Amount()
            device.observables.append(c3)
            c3.id = id + "3"
            c3.name = f"lumen {id}"
            c3.description = f"Current lumen (luminous flux) for {id} color leds"
            c3.quantityType = 'luminousFlux'
            c3.unit = 'lm'
            c3.category = 'internal'
            c3.expr = BinaryOpExpr(op=BinaryOp.MULTIPLY,
                                   expr1=ObservableExpr(id+'1'),
                                   expr2=ConvertExpr(expr=ObservableExpr(id+'2'),quantity='fraction',fromUnit='%',toUnit='_fraction'))
            c3.precision = 1.0

        a2 = cast(Amount, device.observables[1])
        a2.driver = None
        a2.operations = None
        a2.name = "maxLumen"
        a2.description = "Maximum lumen"
        a2.quantityType = 'luminousFlux'
        a2.unit = 'ln'
        a2.expr = ValueExpr(lum)

        a3 = cast(Amount, device.observables[2])
        def add(ids: list[str]) -> Expr:
            id = ids[0]
            oe = ObservableExpr(id+'3')
            if len(ids) == 1:
                return oe
            else:
                return BinaryOpExpr(op=BinaryOp.ADD, expr1=oe, expr2=add(ids[1:]))
        a3.expr = add(color_id)

        a5 = cast(Amount, device.observables[4])
        a5.operations = None
        a5.expr = BinaryOpExpr(op=BinaryOp.MULTIPLY,
                               expr1=ValueExpr(100),
                               expr2=BinaryOpExpr(op=BinaryOp.DIVIDE, expr1=ObservableExpr('A3'), expr2=ObservableExpr('A2')))

        return device

    async def _subscribe(self):
        return await self.hal.subscribe(self._rx_bt, service_uuid='6e400001-b5a3-f393-e0a9-e50e24dcca9e')
