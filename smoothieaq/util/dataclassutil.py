from copy import deepcopy
from dataclasses import *


def overwrite[T](v1: T, v2: T) -> T:
    # returns a deep copy of v1 where all from v2 has been overwriting in v1
    # T must (recursively) be basic type, list or dataclass

    def overwrite_dc[T](dc1: T, dc2: T) -> T:
        assert type(dc1) is type(dc2)
        dc = deepcopy(dc1)
        for field in fields(dc):
            setattr(dc, field.name, overwrite(getattr(dc1, field.name), getattr(dc2, field.name)))
        return dc

    def overwrite_list[T](l1: list[T], l2: list[T]) -> list[T]:

        def do_list() -> list[T]:
            l = deepcopy(l1)
            for i in range(len(l2)):
                if i >= len(l1):
                    l.append(l2[i])
                else:
                    l[i] = overwrite(l1[i],l2[i])
            return l

        def do_dict(key: str) -> list[T]:
            d = dict([(getattr(v, key), v) for v in l1])
            for v2 in l2:
                k2 = getattr(v2, key)
                d[key] = overwrite(d.get(key, None), v2)
            return list(d.values())

        if len(l2) == 0:
            return l1
        if getattr(l2[0], "id", None):
            return do_dict("id")
        elif getattr(l2[0], "key", None):
            return do_dict("key")
        else:
            return do_list()

    if v1 is None:
        return v2
    if v2 is None:
        return v1

    if type(v2) is list:
        return overwrite_list(v1, v2)
    elif is_dataclass(v2):
        return overwrite_dc(v1, v2)
    else:
        return v2




