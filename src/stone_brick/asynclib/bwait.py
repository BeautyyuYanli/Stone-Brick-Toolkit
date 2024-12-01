import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Awaitable, Optional, TypeVar
import logging

T = TypeVar("T")

logger = logging.getLogger(__name__)


async def wrap_awaitable(awaitable: Awaitable[T]):
    """Wraps an awaitable to coroutine."""
    return await awaitable


def bwait(awaitable: Awaitable[T]) -> T:
    """
    Blocks until an awaitable completes and returns its result.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, wrap_awaitable(awaitable)).result()
