import asyncio
from typing import (
    Any,
    Awaitable,
    Generator,
    Generic,
    Tuple,
    TypeVar,
    Union,
)
from stone_brick.observability import instrument

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
to the top-level event loop, then/or get the result T.

The difference between yellow and red/async functions, is that 
red/async functions are always submitted to the event loop.
But yellow functions will only be submitted when encountering 
`yield Awaitable`. 
Otherwise, it simply call yellow functions in the stack.

To convert a blue/sync function to a yellow function, we need to 
wrap the return value with `CWaitValue`, and find the caller chain to 
use `yield from` to call the yellow function. This still introduces
the problem of coloring: just use yellow instead of red.
"""

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
    print("await_c start")

    try:
        x = next(cwaitable)
    except StopIteration as e:
        return e.value

    cnt = 1
    while True:
        try:
            print(f"await_c submit async func {cnt} times")
            result = await x  # type: ignore
            x = cwaitable.send(result)
            cnt += 1
        except StopIteration as e:
            print("await_c ends")
            return e.value


@instrument
async def red_task(x: int):
    print("red_task start")
    await asyncio.sleep(x)
    print("red_task ends")
    return x


@instrument
def blue_task(x: int):
    return x


# Yellow function to call red function
# The keyword is `yield`
@instrument
def yellow_call_red(x: int) -> CWaitable[int]:
    print("yellow_call_red start")
    res1 = yield red_task(x)
    print("yellow_call_red ends")
    return res1


# Yellow function to call blue function. Using CWaitValue to wrap the result.
@instrument
def yellow_call_blue(x: int):
    print("yellow_call_blue")
    ans = blue_task(x)
    return CWaitValue(ans)


# Yellow function to call yellow function in sync manner
# The keyword is `yield from`
@instrument
def yellow_call_yellow(x: int, y: int, z: int) -> CWaitable[int]:
    print("yellow_call_yellow start")
    res1 = yield from yellow_call_red(x)
    res2 = yield from yellow_call_red(y)
    res3 = yield from yellow_call_blue(z)
    print("yellow_call_yellow ends")
    return res1 + res2 + res3


# Yellow function to call yellow function in async manner
# The keyword is `yield await_c(...)`
@instrument
def yellow_call_yellow_async(x: int, y: int, z: int) -> CWaitable[int]:
    print("yellow_call_yellow_async start")
    res: Tuple[int, int, int] = yield asyncio.gather(
        await_c(yellow_call_red(x)),
        await_c(yellow_call_red(y)),
        await_c(yellow_call_blue(z)),
    )
    print("yellow_call_yellow_async ends")
    return res[0] + res[1] + res[2]


if __name__ == "__main__":
    from time import time

    import logfire

    logfire.configure()

    t0 = time()
    print(asyncio.run(await_c(yellow_call_yellow(1, 2, 3))))
    t1 = time()
    print(f"====== yellow_call_yellow cost {t1 - t0} seconds ======")

    print(asyncio.run(await_c(yellow_call_yellow_async(1, 2, 3))))
    print(f"====== yellow_call_yellow_async cost {time() - t1} seconds ======")
