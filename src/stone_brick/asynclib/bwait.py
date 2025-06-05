import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable, Literal, Type, TypeVar, Union

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")

logger = logging.getLogger(__name__)


async def wrap_awaitable(awaitable: Awaitable[T]):
    """Wraps an awaitable to coroutine."""
    return await awaitable


class _NotAsyncWorker:
    pass


def run_in_anyio_worker(
    awaitable: Callable[[], Awaitable[T]],
) -> Union[T, Type[_NotAsyncWorker]]:
    """Code are copied from anyio.from_thread.run to catch the case that not in anyio worker thread."""
    try:
        from anyio._core._eventloop import threadlocals
    except ImportError:
        return _NotAsyncWorker
    else:
        try:
            async_backend = threadlocals.current_async_backend
            token = threadlocals.current_token
        except AttributeError:
            return _NotAsyncWorker

        return async_backend.run_async_from_thread(awaitable, args=(), token=token)


AsyncBackend = Literal["auto", "anyio_worker", "asyncio"]


def bwait(awaitable: Awaitable[T], backend: AsyncBackend = "auto") -> T:
    """
    Blocks until an awaitable completes and returns its result.
    """
    if backend in ("auto", "anyio_worker"):
        res = run_in_anyio_worker(lambda: awaitable)
        if res is not _NotAsyncWorker:
            return res  # type: ignore
        elif backend == "anyio_worker":
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
