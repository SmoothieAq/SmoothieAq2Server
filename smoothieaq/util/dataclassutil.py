from copy import deepcopy
from dataclasses import *
from enum import Enum


def overwrite[T](original: T, overwrite_with: T) -> T:
    # returns a deep copy of v1 where all from v2 has been overwritten in v1
    # T must (recursively) be basic type, list or dataclass

    def overwrite_dc[T](original_dc: T, overwrite_with_dc: T) -> T:
        if not type(original_dc) is type(overwrite_with_dc):
            return overwrite_with_dc
        dc = deepcopy(original_dc)
        for field in fields(dc):
            # print("??",field.name,"??",getattr(original_dc, field.name),"??",getattr(overwrite_with_dc, field.name),"??",overwrite(getattr(original_dc, field.name), getattr(overwrite_with_dc, field.name)))
            setattr(dc, field.name, overwrite(getattr(original_dc, field.name), getattr(overwrite_with_dc, field.name)))
        return dc

    def overwrite_list[T](original_l: list[T], overwrite_with_l: list[T]) -> list[T]:

        def do_list() -> list[T]:
            l = deepcopy(original_l)
            for i in range(len(overwrite_with_l)):
                if i >= len(original_l):
                    l.append(overwrite_with_l[i])
                else:
                    l[i] = overwrite(original_l[i], overwrite_with_l[i])
            return l

        def do_dict(key: str) -> list[T]:
            d = dict([(getattr(v, key), v) for v in deepcopy(original_l)])
            # print(">d1",d)
            for v2 in overwrite_with_l:
                k2 = getattr(v2, key)
                # print(f">>>{k2}<>{d.get(k2, None)}<>{v2}<")
                d[k2] = overwrite(d.get(k2, None), v2)
            # print(">d2",d)
            return list(d.values())

        if len(overwrite_with_l) == 0:
            return original_l
        if getattr(overwrite_with_l[0], "id", None):
            return do_dict("id")
        elif getattr(overwrite_with_l[0], "key", None):
            return do_dict("key")
        else:
            return do_list()

    if original is None:
        return overwrite_with
    if overwrite_with is None:
        return original

    if isinstance(overwrite_with, Enum):
        return overwrite_with
    elif type(overwrite_with) is list:
        return overwrite_list(original, overwrite_with)
    elif is_dataclass(overwrite_with):
        return overwrite_dc(original, overwrite_with)
    else:
        # print("!!",original,"!!",overwrite_with)
        return overwrite_with




