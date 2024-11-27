import asyncio
import time
from unittest import TestCase

from stone_brick.asynclib import bwait
from stone_brick.asynclib.bwait import _pool


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

        assert len(_pool._available_runners) == 2  # noqa: PLR2004
