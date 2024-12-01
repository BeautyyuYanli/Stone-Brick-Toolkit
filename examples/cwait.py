import asyncio
import logging
from typing import Tuple

from stone_brick.asynclib import CWaitable, CWaitValue, await_c
from stone_brick.observability import instrument, instrument_cwaitable

logger = logging.getLogger(__name__)


@instrument
async def red_task(x: int):
    logger.info("red_task start")
    await asyncio.sleep(x)
    logger.info("red_task ends")
    return x


@instrument
def blue_task(x: int):
    return x


# Yellow function to call red function
# The keyword is `yield`
@instrument_cwaitable
def yellow_call_red(x: int) -> CWaitable[int]:
    logger.info("yellow_call_red start")
    res1 = yield red_task(x)
    logger.info("yellow_call_red ends")
    return res1


# Yellow function to call blue function.
# Using CWaitValue to wrap the result.
@instrument
def yellow_call_blue(x: int):
    logger.info("yellow_call_blue")
    ans = blue_task(x)
    return CWaitValue(ans)


# Yellow function to call yellow function in sync manner
# The keyword is `yield from`
@instrument_cwaitable
def yellow_call_yellow(x: int, y: int, z: int) -> CWaitable[int]:
    logger.info("yellow_call_yellow start")
    res1 = yield from yellow_call_red(x)
    res2 = yield from yellow_call_red(y)
    res3 = yield from yellow_call_blue(z)
    logger.info("yellow_call_yellow ends")
    return res1 + res2 + res3


# Yellow function to call yellow function in async manner
# The keyword is `yield await_c(...)`
@instrument_cwaitable
def yellow_call_yellow_async(x: int, y: int, z: int) -> CWaitable[int]:
    logger.info("yellow_call_yellow_async start")
    res: Tuple[int, int, int] = yield asyncio.gather(
        await_c(yellow_call_red(x)),
        await_c(yellow_call_red(y)),
        await_c(yellow_call_blue(z)),
    )
    logger.info("yellow_call_yellow_async ends")
    return res[0] + res[1] + res[2]


if __name__ == "__main__":
    from time import time

    # import logfire

    # logfire.configure()
    # logging.basicConfig(level=logging.INFO, handlers=[logfire.LogfireLoggingHandler()])

    logger.info("start")
    t0 = time()
    print(asyncio.run(await_c(yellow_call_yellow(1, 2, 3))))
    t1 = time()
    print(f"====== yellow_call_yellow cost {t1 - t0} seconds ======")

    print(asyncio.run(await_c(yellow_call_yellow_async(1, 2, 3))))
    print(f"====== yellow_call_yellow_async cost {time() - t1} seconds ======")
