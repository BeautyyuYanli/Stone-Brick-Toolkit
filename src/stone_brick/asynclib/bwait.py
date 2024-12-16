import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable, TypeVar

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")

logger = logging.getLogger(__name__)


async def wrap_awaitable(awaitable: Awaitable[T]):
    """Wraps an awaitable to coroutine."""
    return await awaitable


def bwait(awaitable: Awaitable[T]) -> T:
    """
    Blocks until an awaitable completes and returns its result.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, wrap_awaitable(awaitable)).result()


P = ParamSpec("P")


def bwaiter(func: Callable[P, Awaitable[T]]) -> Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return bwait(func(*args, **kwargs))

    return wrapper
