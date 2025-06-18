import asyncio
import time

from stone_brick.asynclib import CWaitable, await_c, bwait, gather


def test_bwait():
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


def test_cwait():
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


def test_cwait_parallel():
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
    asyncio.run(await_c(to_be_tested(TEST_TIME1, TEST_TIME2)))
    t1 = time.time()

    # Total time should be close to max(TEST_TIME1, TEST_TIME2)
    assert (
        max(TEST_TIME1, TEST_TIME2) - TOLERANCE
        < t1 - t0
        < max(TEST_TIME1, TEST_TIME2) + TOLERANCE
    )


def test_gather_basic():
    """Test basic gather functionality with successful coroutines"""

    async def delay_and_return(sec: float, value: int) -> int:
        await asyncio.sleep(sec)
        return value

    async def run_test():
        results = await gather(
            delay_and_return(0.1, 1),
            delay_and_return(0.2, 2),
            delay_and_return(0.1, 3),
        )
        return results

    results = asyncio.run(run_test())
    assert results == [1, 2, 3]
    assert len(results) == 3


def test_gather_with_exceptions():
    """Test gather functionality when some coroutines raise exceptions"""

    async def success_coro(value: int) -> int:
        await asyncio.sleep(0.1)
        return value

    async def error_coro(msg: str) -> int:
        await asyncio.sleep(0.1)
        raise ValueError(msg)

    async def run_test():
        results = await gather(
            success_coro(1),
            error_coro("test error"),
            success_coro(3),
        )
        return results

    results = asyncio.run(run_test())

    # First and third should be successful
    assert results[0] == 1
    assert results[2] == 3

    # Second should be an exception
    assert isinstance(results[1], ValueError)
    assert str(results[1]) == "test error"


def test_gather_empty():
    """Test gather with no coroutines"""

    async def run_test():
        results = await gather()
        return results

    results = asyncio.run(run_test())
    assert results == []


def test_gather_single_coroutine():
    """Test gather with a single coroutine"""

    async def single_coro() -> str:
        await asyncio.sleep(0.1)
        return "single"

    async def run_test():
        results = await gather(single_coro())
        return results

    results = asyncio.run(run_test())
    assert results == ["single"]


def test_gather_batch_size_unlimited():
    """Test gather with default unlimited batch size"""

    async def delay_coro(delay: float, value: int) -> int:
        await asyncio.sleep(delay)
        return value

    async def run_test():
        # All should run concurrently
        t0 = time.time()
        results = await gather(
            delay_coro(0.2, 1),
            delay_coro(0.2, 2),
            delay_coro(0.2, 3),
            delay_coro(0.2, 4),
        )
        t1 = time.time()
        return results, t1 - t0

    results, elapsed = asyncio.run(run_test())

    assert results == [1, 2, 3, 4]
    # Should complete in ~0.2 seconds since all run concurrently
    assert elapsed < 0.4  # Allow some tolerance


def test_gather_batch_size_limited():
    """Test gather with limited batch size"""

    async def delay_coro(delay: float, value: int) -> int:
        await asyncio.sleep(delay)
        return value

    async def run_test():
        # Limit to 2 concurrent tasks
        t0 = time.time()
        results = await gather(
            delay_coro(0.2, 1),
            delay_coro(0.2, 2),
            delay_coro(0.2, 3),
            delay_coro(0.2, 4),
            batch_size=2,
        )
        t1 = time.time()
        return results, t1 - t0

    results, elapsed = asyncio.run(run_test())

    assert results == [1, 2, 3, 4]
    # Should take ~0.4 seconds (2 batches of 0.2 seconds each)
    assert elapsed > 0.35  # Should be longer than single batch
    assert elapsed < 0.6  # But not too long


def test_gather_batch_size_one():
    """Test gather with batch size of 1 (sequential execution)"""

    async def delay_coro(delay: float, value: int) -> int:
        await asyncio.sleep(delay)
        return value

    async def run_test():
        t0 = time.time()
        results = await gather(
            delay_coro(0.1, 1), delay_coro(0.1, 2), delay_coro(0.1, 3), batch_size=1
        )
        t1 = time.time()
        return results, t1 - t0

    results, elapsed = asyncio.run(run_test())

    assert results == [1, 2, 3]
    # Should take ~0.3 seconds (3 tasks × 0.1 seconds each)
    assert elapsed > 0.25
    assert elapsed < 0.4


def test_gather_mixed_types():
    """Test gather with coroutines returning different types"""

    async def int_coro() -> int:
        await asyncio.sleep(0.1)
        return 42

    async def str_coro() -> str:
        await asyncio.sleep(0.1)
        return "hello"

    async def bool_coro() -> bool:
        await asyncio.sleep(0.1)
        return True

    async def run_test():
        results = await gather(int_coro(), str_coro(), bool_coro())
        return results

    results = asyncio.run(run_test())
    assert results == [42, "hello", True]
