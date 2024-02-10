import smoothieaq.model.enum as aqe
from pydantic import RootModel, TypeAdapter
from pydantic_yaml import to_yaml_str, parse_yaml_raw_as, parse_yaml_file_as


def enum_test() -> str:
    e1 = aqe.EnumSimple(id='e1', description='de1', name='ne1')
    e1.values = [aqe.EnumValueSimple(id='v1', name='nv1')]

    q1 = aqe.QuantityType(id="length", name='Length')
    q1.values = [aqe.Unit(id="m", name="meter"), aqe.Unit(id='cm', name='centimeter', relTimes=1 / 100, relUnit='m')]

    el = [e1, q1]

    print(el)
    print('\n')
    print(TypeAdapter(aqe.Enum).json_schema())
    print('\n')
    json = TypeAdapter(list[aqe.Enum]).dump_json(el, exclude_none=True, exclude_unset=True)
    print(json)
    el2 = TypeAdapter(list[aqe.Enum]).validate_json(json)
    print('\n')
    print(el2)
    print('\n')
    yaml_str = to_yaml_str(RootModel[list[aqe.Enum]](el), exclude_none=True, exclude_unset=True)
    print(yaml_str)
    print('\n')

    el3: list[aqe.Enum] = parse_yaml_raw_as(RootModel[list[aqe.Enum]], yaml_str).root
    print(el3)

    el4: list[aqe.Enum] = parse_yaml_file_as(RootModel[list[aqe.Enum]], "resources/enums.yaml").root
    print(el4)

    return "thuhej"
