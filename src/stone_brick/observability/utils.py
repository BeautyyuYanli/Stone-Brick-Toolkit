from typing import Callable, TypeVar

from typing_extensions import ParamSpec

try:
    from opentelemetry import trace
except ImportError:
    trace = None

P = ParamSpec("P")
T = TypeVar("T")


def instrument(function: Callable[P, T]) -> Callable[P, T]:
    if trace is None:
        return function
    tracer = trace.get_tracer(function.__module__)
    return tracer.start_as_current_span(function.__name__)(function)  # type: ignore
