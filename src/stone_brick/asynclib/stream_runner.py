import math
from contextlib import asynccontextmanager
from typing import (
    Generic,
    TypeVar,
)

import anyio
from anyio import create_memory_object_stream
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from exceptiongroup import BaseExceptionGroup
from typing_extensions import Awaitable

from stone_brick.asynclib.common import NoResult

TStream = TypeVar("TStream")
TRes = TypeVar("TRes")


class StreamRunner(Generic[TStream, TRes]):
    _closed: bool
    _result: TRes | NoResult
    _consumer: MemoryObjectReceiveStream[TStream]
    producer: MemoryObjectSendStream[TStream]

    @property
    def result(self) -> TRes:
        if isinstance(self._result, NoResult):
            raise self._result
        return self._result

    def __init__(self):
        self._closed = False
        self.producer, self._consumer = create_memory_object_stream(
            max_buffer_size=math.inf
        )
        self._result = NoResult()

    def __enter__(self):
        if self._closed:
            raise RuntimeError("StreamRunner is already closed")
        return self

    async def __aenter__(self):
        if self._closed:
            raise RuntimeError("StreamRunner is already closed")
        return self

    def close(self):
        self._closed = True
        self.producer.close()
        self._consumer.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.close()

    async def _loop(self):
        async for event in self._consumer:
            yield event

    @asynccontextmanager
    async def run(self, target: Awaitable[TRes]):
        async def _warp():
            try:
                self._result = await target
            finally:
                self.producer.close()  # Close the producer

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(_warp)
                try:
                    yield self._loop()
                finally:
                    tg.cancel_scope.cancel()
        except BaseExceptionGroup as exc_group:
            # Re-raise the first exception from the group
            # That is, the exception is raised from
            if exc_group.exceptions:
                raise exc_group.exceptions[0] from None
            raise


if __name__ == "__main__":

    async def foo(
        producer: MemoryObjectSendStream[int],
        raise_exception: bool = False,
        return_value: bool = False,
    ) -> str:
        cnt = 0
        while True:
            print(f"Sending {cnt}")
            await producer.send(cnt)
            cnt += 1
            if cnt > 3:
                if raise_exception:
                    raise Exception("Hiya!")
                if return_value:
                    return "Fuyo!"

    async def example_1():
        """This example shows a normal case"""
        async with (
            StreamRunner[int, str]() as runner,
            runner.run(foo(runner.producer, return_value=True)) as loop,
        ):
            async for event in loop:
                print(event)

    async def example_2():
        """This example shows a case where the producer raise exception"""

        async with (
            StreamRunner[int, str]() as runner,
            runner.run(foo(runner.producer, raise_exception=True)) as loop,
        ):
            async for event in loop:
                print(event)

    async def example_3():
        """This example shows a case where the consumer raise exception"""
        async with (
            StreamRunner[int, str]() as runner,
            runner.run(foo(runner.producer)) as loop,
        ):
            async for event in loop:
                print(event)
                raise Exception("Oops!")

    async def example_4():
        """This example shows a case where the consumer early exit"""
        async with (
            StreamRunner[int, str]() as runner,
            runner.run(foo(runner.producer)) as loop,
        ):
            async for event in loop:
                print(event)
                break
            print(runner.result)

    anyio.run(example_1)

    try:
        anyio.run(example_2)
    except Exception as e:
        assert e.args[0] == "Hiya!"
    else:
        raise AssertionError("Should have raised an exception")

    try:
        anyio.run(example_3)
    except Exception as e:
        assert e.args[0] == "Oops!"
    else:
        raise AssertionError("Should have raised an exception")

    try:
        anyio.run(example_4)
    except Exception as e:
        assert isinstance(e, NoResult)
    else:
        raise AssertionError("Should have raised an exception")
