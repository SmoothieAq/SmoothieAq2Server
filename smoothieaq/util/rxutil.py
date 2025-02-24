import asyncio
import logging
from asyncio import sleep
from typing import Callable, TypeVar, Iterable, Optional, NoReturn, Awaitable

import aioreactive as rx
from aioreactive import AsyncObservable, AsyncObserver, AsyncAnonymousObservable, SendAsync, ThrowAsync, CloseAsync
from aioreactive.msg import Msg
from aioreactive.notification import Notification, OnNext, OnError, OnCompleted
from aioreactive.observers import auto_detach_observer, AsyncNotificationObserver, AsyncAnonymousObserver
from aioreactive.subject import AsyncMultiSubject
from aioreactive.types import _T_out
from aioreactive.create import interval
from expression import MailboxProcessor, pipe, tailrec_async, TailCallResult, TailCall, snd
from expression.collections import Seq
from expression.collections.seq import of_iterable
from expression.system import AsyncDisposable

log = logging.getLogger(__name__)

_TSource = TypeVar("_TSource")


def buffer(
        boundaries: AsyncObservable[any], count: int = 0, emitEmpty: bool = True
) -> Callable[[AsyncObservable[_TSource]], AsyncObservable[list[_TSource]]]:
    def _buffer(source: AsyncObservable[_TSource]) -> AsyncObservable[_TSource]:
        async def subscribe_async(aobv: AsyncObserver[_TSource]) -> AsyncDisposable:
            safe_obv, auto_detach = auto_detach_observer(aobv)

            async def worker(inbox: MailboxProcessor[Msg[_TSource]]) -> None:

                async def message_loop() -> None:
                    buffer: list[_TSource] = []

                    while True:
                        cn = await inbox.receive()

                        match cn:
                            case Msg(tag="source", source=value):
                                match value:
                                    case OnNext(value=value):
                                        buffer.append(value)
                                        if len(buffer) == count:
                                            await safe_obv.asend(buffer)
                                            buffer = []
                                    case OnError(exception=err):
                                        await safe_obv.athrow(err)
                                        return
                                    case _:
                                        if len(buffer) > 0:
                                            await safe_obv.asend(buffer)
                                        await safe_obv.aclose()
                                        return

                            case Msg(tag="other", other=value):
                                match value:
                                    case OnNext(value=value):
                                        if len(buffer) > 0 or emitEmpty:
                                            await safe_obv.asend(buffer)
                                            buffer = []
                                    case OnError(exception=err):
                                        await safe_obv.athrow(err)
                                        return
                                    case _:
                                        if len(buffer) > 0:
                                            await safe_obv.asend(buffer)
                                        await safe_obv.aclose()
                                        return

                            case _:
                                raise ValueError(f"Unexpected message: {cn}")

                await message_loop()

            agent = MailboxProcessor.start(worker)

            async def obv_fn1(n: Notification[_TSource]) -> None:
                agent.post(Msg(source=n))

            async def obv_fn2(n: Notification[any]) -> None:
                agent.post(Msg(other=n))

            obv1: AsyncObserver[_TSource] = AsyncNotificationObserver(obv_fn1)
            obv2: AsyncObserver[any] = AsyncNotificationObserver(obv_fn2)
            dispose1 = await pipe(obv1, source.subscribe_async, auto_detach)
            dispose2 = await pipe(obv2, boundaries.subscribe_async, auto_detach)

            return AsyncDisposable.composite(dispose1, dispose2)

        return AsyncAnonymousObservable(subscribe_async)

    return _buffer


def buffer_with_time(
        seconds: float, count: int = 0, emitEmpty: bool = False
) -> Callable[[AsyncObservable[_TSource]], AsyncObservable[list[_TSource]]]:
    return buffer(interval(seconds, seconds), count=count, emitEmpty=emitEmpty)


async def _buffer_test():
    async def do(n):
        print(n)
    await pipe(
        interval(seconds=0, period=0.6),
        rx.take(20),
        buffer_with_time(2, count=3),
        rx.subscribe_async(rx.AsyncAnonymousObserver(do)))
    await sleep(15)


class AsyncBehaviorSubject[_TSource](AsyncMultiSubject):

    def __init__(self, initialValue: _TSource):
        super().__init__()
        self.value = initialValue

    async def asend(self, value: _TSource) -> None:
        self.value = value
        self.check_disposed()

        if self._is_stopped:
            return

        for obv in list(self._observers):
            await obv.asend(value)

    async def subscribe_async(
        self,
        send: SendAsync[_TSource] | AsyncObserver[_TSource] | None = None,
        throw: ThrowAsync | None = None,
        close: CloseAsync | None = None,
    ) -> AsyncDisposable:
        """Subscribe."""
        log.debug("AsyncMultiStream:subscribe_async()")
        self.check_disposed()

        observer = send if isinstance(send, AsyncObserver) else AsyncAnonymousObserver(send, throw, close)
        await observer.asend(self.value)  # initial value
        self._observers.append(observer)

        async def dispose() -> None:
            log.debug("AsyncMultiStream:dispose()")
            if observer in self._observers:
                self._observers.remove(observer)

        return AsyncDisposable.create(dispose)


class AsyncConnectableObservable(AsyncObservable[_TSource]):

    def __init__(self, source: AsyncObservable[_TSource], initialValue: Optional[_TSource] = None):
        self.source = source
        self.subject = AsyncBehaviorSubject(initialValue) if initialValue is not None else rx.AsyncSubject()
        super().__init__()

    async def subscribe_async(
        self,
        send: SendAsync[_T_out] | AsyncObserver[_T_out] | None = None,
        throw: ThrowAsync | None = None,
        close: CloseAsync | None = None,
    ) -> AsyncDisposable:
        return await self.subject.subscribe_async(send, throw, close)

    async def connect(self) -> AsyncDisposable:
        return await self.source.subscribe_async(self.subject)


def publish(
        initialValue: Optional[_TSource] = None
) -> Callable[[AsyncObservable[_TSource]], AsyncConnectableObservable[_TSource]]:
    def _publish(source: AsyncObservable[_TSource]) -> AsyncConnectableObservable[_TSource]:
        return AsyncConnectableObservable(source, initialValue)

    return _publish


async def _behavior_test():
    subject = AsyncBehaviorSubject(9)
    def p(n):
        async def _p(v):
            print(n, v)
        return _p
    await subject.subscribe_async(p("a"))
    await subject.asend(1)
    await subject.subscribe_async(p("b"))
    await subject.asend(2)
    await sleep(2)


async def _publish_test():
    def p(n):
        async def _p(v):
            print(n, v)
        return _p
    obs = rx.pipe(interval(seconds=1, period=0.6), publish(99))
    await obs.connect()
    await sleep(2)
    await obs.subscribe_async(p("a"))
    await sleep(2)
    await obs.subscribe_async(p("b"))
    await sleep(2)


def distinct_until_changed(
        comparer: Callable[[_TSource, _TSource], bool] = lambda v1, v2: v1 == v2
) -> Callable[[AsyncObservable[_TSource]], AsyncObservable[_TSource]]:
    def _distinct_until_changed(
        source: AsyncObservable[_TSource],
    ) -> AsyncObservable[_TSource]:
        async def subscribe_async(aobv: AsyncObserver[_TSource]) -> AsyncDisposable:
            safe_obv, auto_detach = auto_detach_observer(aobv)

            async def worker(inbox: MailboxProcessor[Notification[_TSource]]) -> None:
                @tailrec_async
                async def message_loop(
                    latest: _TSource | None,
                ) -> TailCallResult[NoReturn, [_TSource | None]]:
                    n = await inbox.receive()

                    async def get_latest() -> _TSource | None:
                        match n:
                            case OnNext(value=x):
                                try:
                                    if (latest is None and x is not None) or not comparer(latest, x):
                                        await safe_obv.asend(x)
                                except Exception as ex:
                                    await safe_obv.athrow(ex)
                                return x
                            case OnError(exception=err):
                                await safe_obv.athrow(err)

                            case _:
                                await safe_obv.aclose()

                        return None

                    latest = await get_latest()
                    return TailCall[_TSource | None](latest)

                await message_loop(None)

            agent = MailboxProcessor.start(worker)

            async def notification(n: Notification[_TSource]) -> None:
                agent.post(n)

            obv: AsyncObserver[_TSource] = AsyncNotificationObserver(notification)
            return await pipe(obv, source.subscribe_async, auto_detach)

        return AsyncAnonymousObservable(subscribe_async)

    return _distinct_until_changed


async def _distinct_until_changed_test():
    async def p(n):
        print(n)
    sub = rx.AsyncSubject()
    # await pipe(sub, distinct_until_changed()).subscribe_async(p)
    # await sub.asend((1,2))
    # await sub.asend((1,3))
    # await sub.asend((1,3))
    # await sub.asend((2,2))
    # await sub.asend((2,3))
    # await sub.asend((2,3))
    # await sub.aclose()
    await pipe(sub, distinct_until_changed(lambda a, b: a[0] == b[0])).subscribe_async(p,p)
    await sub.asend((1,2))
    await sub.asend((1,3))
    await sub.asend((1,3))
    await sub.asend((2,2))
    await sub.asend((2,3))
    await sub.asend((2,3))
    await sub.aclose()
    await sleep(2)


def sample(
        sampler: AsyncObservable[any] | float
) -> Callable[[AsyncObservable[_TSource]], AsyncObservable[_TSource]]:
    frm = interval(5,5) # sampler if isinstance(sampler, AsyncObservable) else interval(sampler, sampler)

    def _sample(source: AsyncObservable[_TSource]) -> AsyncObservable[_TSource]:
        return pipe(frm, rx.with_latest_from(source), rx.map(snd))

    return _sample


def trace(
        label: str = "trace"
) -> Callable[[AsyncObservable[_TSource]], AsyncObservable[_TSource]]:
    def _trace(n: _TSource) -> _TSource:
        print("-->", label, n)
        return n
    return rx.map(_trace)


async def take_first[T](obs: AsyncObservable[T], do: Callable[[T], None]) -> None:
    async def do_it(t: T) -> None:
        try:
            do(t)
        finally:
            await disposable.dispose_async()

    disposable = await rx.pipe(obs, rx.take(1)).subscribe_async(do_it)


async def take_first_async[T](obs: AsyncObservable[T], do: Callable[[T], Awaitable[None]]) -> None:
    async def do_it(t: T) -> None:
        try:
            await do(t)
        finally:
            await disposable.dispose_async()

    disposable = await rx.pipe(obs, rx.take(1)).subscribe_async(do_it)


async def await_first[T](obs: AsyncObservable[T]) -> T:
    fut: asyncio.Future[T] = asyncio.get_running_loop().create_future()
    def _fut(t: T): fut.set_result(t)
    await take_first(obs, _fut)
    return await fut


def throw_it(txt: str):
    async def _err(ex: Exception):
        print(f"!!! {txt} {self.id}", ex)
        log.error(f"{txt} {self.id}", exc_info=ex)

    return _err


def print_it(txt: str):
    async def _print(e):
        print(f"!!! {txt} {self.id}", e)

    return _print


def ix(i: Iterable[_TSource]) -> Seq[_TSource]:
    return of_iterable(i)


def x(source: AsyncObservable[_TSource]) -> rx.AsyncRx[_TSource]:
    return rx.AsyncRx(source)


async def do_later(delay: float, do: Callable[[], Awaitable[None]]) -> None:
    async def do_it(n: int) -> None:
        try:
            await do()
        finally:
            await disposable.dispose_async()

    disposable = await rx.interval(delay, 2).subscribe_async(do_it)
