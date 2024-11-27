import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Awaitable, Optional, TypeVar

T = TypeVar("T")

cpu_cnt = os.cpu_count()


class AsyncRunner:
    """A thread runner for async tasks."""

    _thread: threading.Thread
    _loop: asyncio.AbstractEventLoop

    def __init__(self):
        started = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop, args=(started,), daemon=True
        )
        self._thread.start()
        started.wait()

    def _run_loop(self, started: threading.Event):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        started.set()
        self._loop.run_forever()

    def run_async(self, awaitable: Awaitable[T]) -> T:
        future = asyncio.run_coroutine_threadsafe(awaitable, self._loop)
        return future.result()


@dataclass
class AsyncRunnerPool:
    """Manages a pool of AsyncRunner instances."""

    max_free_runners: Optional[int] = field(default=cpu_cnt)
    _pool_lock: threading.Lock = field(default_factory=threading.Lock)
    _available_runners: set[AsyncRunner] = field(default_factory=set)

    @contextmanager
    def get_runner(self):
        """
        Gets an available runner from the pool.

        Usage:
            with pool.get_runner() as runner:
                result = runner.run_async(...)
        """
        runner = self._acquire_runner()
        try:
            yield runner
        finally:
            self._release_runner(runner)

    def _acquire_runner(self) -> AsyncRunner:
        """Gets an available runner or creates a new one."""
        with self._pool_lock:
            if self._available_runners:
                return self._available_runners.pop()
            return AsyncRunner()

    def _release_runner(self, runner: AsyncRunner) -> None:
        """Returns a runner to the available pool."""
        with self._pool_lock:
            if (
                self.max_free_runners is None
                or len(self._available_runners) < self.max_free_runners
            ):
                self._available_runners.add(runner)


_pool = AsyncRunnerPool()


async def wrap_awaitable(awaitable: Awaitable[T]):
    """Wraps an awaitable to coroutine."""
    return await awaitable


def bwait(awaitable: Awaitable[T], use_pool: Optional[AsyncRunnerPool] = _pool) -> T:
    """
    Blocks until an awaitable completes and returns its result.
    Uses a pool of background threads for better resource usage.
    """
    if use_pool:
        with _pool.get_runner() as runner:
            return runner.run_async(awaitable)
    else:
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, wrap_awaitable(awaitable)).result()
