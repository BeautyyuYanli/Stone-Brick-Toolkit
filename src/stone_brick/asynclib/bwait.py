import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable, Literal, TypeVar

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")

logger = logging.getLogger(__name__)


async def wrap_awaitable(awaitable: Awaitable[T]):
    """Wraps an awaitable to coroutine."""
    return await awaitable


def in_anyio_worker():
    try:
        from anyio import from_thread
    except ImportError:
        return False
    else:

        async def _():
            return None

        try:
            from_thread.run(_)
        except RuntimeError:
            return False
        return True


AsyncBackend = Literal["auto", "anyio_worker", "asyncio"]


def bwait(awaitable: Awaitable[T], backend: AsyncBackend = "auto") -> T:
    """
    Blocks until an awaitable completes and returns its result.
    """
    if backend in ("auto", "anyio_worker"):
        if in_anyio_worker():
            from anyio import from_thread

            return from_thread.run(lambda: awaitable)
        if backend == "anyio_worker":
            raise RuntimeError("Not in anyio worker thread")

    # Detect usable loop
    pass
    # Fallback to asyncio
    import asyncio

    run = asyncio.run

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(run, wrap_awaitable(awaitable)).result()


P = ParamSpec("P")


def bwaiter(func: Callable[P, Awaitable[T]]) -> Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return bwait(func(*args, **kwargs))

    return wrapper
