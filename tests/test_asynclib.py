import asyncio
import time
from unittest import TestCase

from stone_brick.asynclib import CWaitable, await_c, bwait


class TestBwait(TestCase):
    def test_bwait(self):
        async def first_delay(sec: float):
            await asyncio.sleep(sec)
            return sec

        def first_delay_sync(sec: float):
            ans = bwait(first_delay(sec))
            return ans

        async def second_delay(sec: float):
            return first_delay_sync(sec)

        TEST_TIME = 1
        TOLERANCE = 0.1

        t0 = time.time()
        bwait(second_delay(TEST_TIME))
        t1 = time.time()
        assert TEST_TIME - TOLERANCE < t1 - t0 < TEST_TIME + TOLERANCE


class TestCwait(TestCase):
    def test_cwait(self):
        async def first_delay(sec: float) -> float:
            await asyncio.sleep(sec)
            return sec

        def first_yellow(sec: float) -> CWaitable[float]:
            yield first_delay(sec)
            return sec

        def to_be_tested(sec: float) -> CWaitable[float]:
            yield from first_yellow(sec)
            yield from first_yellow(sec)
            return sec

        TEST_TIME = 1
        TOLERANCE = 0.1

        t0 = time.time()
        asyncio.run(await_c(to_be_tested(TEST_TIME / 2)))
        t1 = time.time()

        # Test timing
        assert TEST_TIME - TOLERANCE < t1 - t0 < TEST_TIME + TOLERANCE

    def test_cwait_parallel(self):
        async def first_delay(sec: float) -> float:
            await asyncio.sleep(sec)
            return sec

        def first_yellow(sec: float) -> CWaitable[float]:
            yield first_delay(sec)
            return sec

        def to_be_tested(sec1: float, sec2: float) -> CWaitable[tuple[float, float]]:
            yield asyncio.gather(
                await_c(first_yellow(sec1)),
                await_c(
                    first_yellow(sec2),
                ),
            )

            return sec1, sec2

        TEST_TIME1 = 1.0
        TEST_TIME2 = 2.0
        TOLERANCE = 0.1

        t0 = time.time()
        t1 = time.time()

        # Total time should be close to max(TEST_TIME1, TEST_TIME2)
        assert (
            max(TEST_TIME1, TEST_TIME2) - TOLERANCE
            < t1 - t0
            < max(TEST_TIME1, TEST_TIME2) + TOLERANCE
        )
