from smoothieaq.div import objectstore
from smoothieaq.model.enum import Enum, EnumSimple, QuantityType, Unit
from smoothieaq.util.rxutil import ix

enums: dict[str, EnumSimple] = dict()
quantities: dict[str, QuantityType] = dict()


def load():
    for e in objectstore.get_all(Enum):
        match e:
            case EnumSimple():
                enums[e.id] = e
            case QuantityType():
                quantities[e.id] = e


def convert(value: float, quantity_id: str, from_unit_id: str, to_unit_id: str):
    if value is None:
        return value
    if from_unit_id == to_unit_id:
        return value
    quantity = quantities[quantity_id]
    units: dict[str, Unit] = dict(ix(quantity.values).map(lambda u: (u.id, u)))

    def to_base(value: float, from_unit_id: str) -> float:
        unit = units[from_unit_id]
        if not unit.relUnit:
            return value
        return to_base(((value - (unit.relAdd or 0)) / (unit.relTimes or 1)), unit.relUnit)

    def to_unit(value: float, to_unit_id: str) -> float:
        unit = units[to_unit_id]
        if not unit.relUnit:
            return value
        return to_unit(value, unit.relUnit) * (unit.relTimes or 1) + (unit.relAdd or 0)

    return to_unit(to_base(value, from_unit_id), to_unit_id)

