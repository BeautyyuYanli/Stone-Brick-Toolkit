from contextlib import asynccontextmanager
from typing import (
    Generic,
    TypeVar,
)

import anyio
from exceptiongroup import BaseExceptionGroup
from typing_extensions import Awaitable

from stone_brick.asynclib.common import NoResult

TStream = TypeVar("TStream")
TRes = TypeVar("TRes")


class ResultContainer(Generic[TRes]):
    _data: TRes | NoResult

    @property
    def data(self) -> TRes:
        if isinstance(self._data, NoResult):
            raise self._data
        return self._data


@asynccontextmanager
async def background_run(target: Awaitable[TRes]):
    result = ResultContainer()

    async def _warp():
        result._data = await target

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(_warp)
            yield result
    except BaseExceptionGroup as exc_group:
        if exc_group.exceptions:
            raise exc_group.exceptions[0] from None
        raise


if __name__ == "__main__":

    async def foo():
        await anyio.sleep(3)
        return "Hello, world!"

    async def example_1():
        async with background_run(foo()) as result:
            print("Waiting for result...")
        print(result.data)

    anyio.run(example_1)
