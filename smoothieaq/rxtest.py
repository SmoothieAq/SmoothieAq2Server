import asyncio
from asyncio import sleep

import reactivex as rx
import reactivex.scheduler
from reactivex import operators as op
from reactivex.scheduler.eventloop import AsyncIOScheduler
from reactivex.scheduler import ThreadPoolScheduler


async def rxtest() -> None:

    s1 = rx.interval(1).pipe( op.map(lambda n: f"a {n}"))
    s2 = rx.interval(1.5).pipe( op.map(lambda n: f"b {n}"))

    #rx.combine_latest(__sources=[s1,s2]).pipe( op.map(lambda v: v[0]+v[1])).subscribe(lambda v: print(v))
#
#     s = rx.Subject[rx.Observable[str]]()
# #    p = rx.from_list([s1,s2]).pipe(op.merge_all()).pipe(op.publish())
#     p = s.pipe(op.merge_all()).pipe(op.publish())
#
#     p.subscribe(lambda s: print(f"x {s}"))
#     p.pipe(op.filter(lambda s: s[0] == "b")).subscribe(lambda s: print(f"y {s}"))
#     p.connect()
#     s.on_next(s1)
#     s.on_next(s2)

    await sleep(5)



