from typing import Any, Coroutine, TypeVar

from anyio import Semaphore, create_task_group

T = TypeVar("T")


async def gather(
    *coros: Coroutine[Any, Any, T], batch_size: int = -1
) -> list[T | Exception]:
    num_coros = len(coros)
    async with create_task_group() as task_group:
        _results: dict[int, T | Exception] = dict()

        if batch_size == -1:
            # No batching - run all tasks concurrently
            async def _run(_idx: int, coro: Coroutine[Any, Any, T]) -> None:
                try:
                    _results[_idx] = await coro
                except Exception as e:
                    _results[_idx] = e

            for idx, coro in enumerate(coros):
                task_group.start_soon(_run, idx, coro)
        else:
            # Use a semaphore to limit concurrent tasks
            semaphore = Semaphore(batch_size)

            async def _run(_idx: int, coro: Coroutine[Any, Any, T]) -> None:
                async with semaphore:
                    try:
                        _results[_idx] = await coro
                    except Exception as e:
                        _results[_idx] = e

            for idx, coro in enumerate(coros):
                task_group.start_soon(_run, idx, coro)

    return [_results[idx] for idx in range(num_coros)]
