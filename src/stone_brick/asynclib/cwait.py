"""
We have invented a new type of function, called `CWaitable` function,
or "yellow function".

Yellow functions must be runned in an async event loop environment.
Or we say, the async event loop is the runtime of yellow functions.

The yellow function can call all colors of functions.

To call a red (async) function, it will yield the Awaitable[T]
to the top-level event loop, and get the result T to continue.

To call a blue (sync) function, it will simply call and return,
with a Generator wrapper.

To call a yellow function, it will simply call and, pass the yield
to the top-level event loop, then/or get the result T to return.

The difference between yellow and red/async functions, is that
red/async functions are always submitted to the event loop.
But yellow functions will only be submitted when encountering
`yield Awaitable`.
Otherwise, it simply call yellow functions in the stack.
This is not meant to resolve the coloring problem, but to simulate
the stackful coroutine, using generator in Python, so that its behavior
is the same as goroutine or system thread.

Check `examples/cwait.py` for more details.
"""

from typing import (
    Any,
    Awaitable,
    Generator,
    Generic,
    TypeVar,
    Union,
)

T = TypeVar("T")
CWaitable = Generator[Awaitable[Any], Any, T]


class CWaitValue(Generator[Any, Any, T], Generic[T]):
    def __init__(self, value: T):
        self.value = value

    def __next__(self) -> T:
        raise StopIteration(self.value)

    def send(self, value: Any) -> T:
        raise StopIteration(self.value)

    def throw(self, typ: Any, val: Any = None, tb: Any = None):
        raise RuntimeError("CWaitValue should not be thrown")


async def await_c(cwaitable: Union[CWaitable[T], CWaitValue[T]]) -> T:
    try:
        x = next(cwaitable)
    except StopIteration as e:
        return e.value

    while True:
        try:
            try:
                result = await x  # type: ignore
            except Exception as e:
                cwaitable.throw(e)
            else:
                x = cwaitable.send(result)
        except StopIteration as e:
            return e.value
