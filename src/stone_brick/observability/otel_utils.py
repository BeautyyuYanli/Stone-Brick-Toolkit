from contextlib import contextmanager
from functools import cache
from typing import TYPE_CHECKING, Callable, TypeVar

from typing_extensions import ParamSpec

try:
    from opentelemetry import trace
except ImportError:
    trace = None

if TYPE_CHECKING:
    from stone_brick.asynclib import CWaitable

P = ParamSpec("P")
T = TypeVar("T")


@cache
def _get_full_name(func):
    return func.__module__ + "." + func.__name__


@cache
def _get_tracer(module: str):
    if trace is None:
        raise RuntimeError("opentelemetry is not installed")
    return trace.get_tracer(module)


def instrument(func: Callable[P, T]) -> Callable[P, T]:
    if trace is None:
        return func
    tracer = _get_tracer(func.__module__)
    return tracer.start_as_current_span(_get_full_name(func))(func)  # type: ignore


def instrument_cwaitable(
    func: Callable[P, "CWaitable[T]"],
) -> Callable[P, "CWaitable[T]"]:
    def wrapper(*args, **kwargs) -> "CWaitable[T]":
        with get_span(func):
            return (yield from func(*args, **kwargs))

    return wrapper  # type: ignore


def get_span(func):
    if trace is None:
        return contextmanager(lambda: iter([()]))()
    tracer = _get_tracer(func.__module__)
    return tracer.start_as_current_span(_get_full_name(func))
