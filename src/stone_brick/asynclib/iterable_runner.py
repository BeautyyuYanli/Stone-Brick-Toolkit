from contextlib import contextmanager
from queue import Queue
from threading import Event, Thread
from typing import AsyncIterable, Callable, Iterable, TypeVar

from stone_brick.asynclib.bwait import AsyncBackend, bwait

T = TypeVar("T")
T2 = TypeVar("T2")


class Finished:
    pass


def iterable_to_queue(
    iterable: Iterable[T], q: Queue[T | BaseException | Finished], stop_event: Event
) -> None:
    """Decouple iterable.__next__ to a queue so that it can be called in a separate thread."""
    try:
        for item in iterable:
            if stop_event.is_set():
                break
            q.put(item)
    except BaseException as e:
        q.put(e)
        return
    else:
        q.put(Finished())


async def aiterable_to_queue(
    aiterable: AsyncIterable[T],
    q: Queue[T | BaseException | Finished],
    stop_event: Event,
) -> None:
    """Decouple aiterable.__anext__ to a queue so that it can be called in a separate thread."""
    try:
        async for item in aiterable:
            if stop_event.is_set():
                break
            q.put(item)
    except BaseException as e:
        q.put(e)
        return
    else:
        q.put(Finished())


def queue_to_iterable(q: Queue[T | BaseException | Finished]) -> Iterable[T]:
    """Collect items from a queue and yield as Iterable."""
    while True:
        item = q.get()
        if isinstance(item, Finished):
            break
        if isinstance(item, BaseException):
            raise item
        yield item


@contextmanager
def stream_to_thread(
    iterable: Iterable[T] | AsyncIterable[T], async_backend: AsyncBackend = "auto"
):
    """Call iterable.__next__ in a separate thread."""
    q: Queue[T | BaseException | Finished] = Queue()
    stop_event = Event()
    if hasattr(iterable, "__aiter__"):

        def target():
            return bwait(aiterable_to_queue(iterable, q, stop_event), async_backend)  # type: ignore
    elif hasattr(iterable, "__iter__"):

        def target():
            return iterable_to_queue(iterable, q, stop_event)  # type: ignore
    else:
        raise TypeError(f"Expected Iterable or AsyncIterable, got {type(iterable)}")
    thread = Thread(
        target=target,
        daemon=True,
    )
    thread.start()
    try:
        yield queue_to_iterable(q)
    finally:
        stop_event.set()
        thread.join()


def stream_trans_to_thread(iterable: Iterable[T], func: Callable[[T], T2]):
    """Call x = iterable.__next__() and then func(x) in a separate thread."""

    def _pipe():
        for item in iterable:
            yield func(item)

    return stream_to_thread(_pipe())
