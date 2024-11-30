from typing import Callable, TypeVar

from typing_extensions import ParamSpec
from contextlib import contextmanager

try:
    from opentelemetry import trace
except ImportError:
    trace = None

P = ParamSpec("P")
T = TypeVar("T")


def get_name(func):
    return func.__module__ + "." + func.__name__


def instrument(function: Callable[P, T]) -> Callable[P, T]:
    if trace is None:
        return function
    tracer = trace.get_tracer(function.__module__)
    return tracer.start_as_current_span(function.__name__)(function)  # type: ignore


def get_span(func):
    if trace is None:
        return contextmanager(lambda: iter([()]))()
    tracer = trace.get_tracer(func.__module__)
    return tracer.start_as_current_span(get_name(func))  # type: ignore
