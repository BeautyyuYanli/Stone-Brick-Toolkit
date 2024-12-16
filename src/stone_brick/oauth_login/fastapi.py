import asyncio
from functools import wraps
from time import time
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    NoReturn,
    TypeVar,
    Union,
)

from typing_extensions import ParamSpec

try:
    from fastapi import HTTPException
except ImportError:
    if TYPE_CHECKING:
        from fastapi import HTTPException
    else:
        HTTPException = None

from stone_brick.oauth_login.providers.common import ProviderError

# Type definitions
T = TypeVar("T")


def oauth_to_http_exception(e: Exception) -> NoReturn:
    """Convert an exception to an HTTPException with appropriate status code."""

    if isinstance(e, ProviderError):
        raise HTTPException(
            status_code=e.status,
            detail={
                "msg": str(e),
                "time": time(),
            },
        ) from e
    raise e


P = ParamSpec("P")


def oauth_handle_exceptions(
    func: Union[Callable[P, T], Callable[P, Awaitable[T]]],
) -> Callable[P, T]:
    """Decorator to automatically handle exceptions and convert them to HTTPExceptions.
    Supports both sync and async functions."""

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            oauth_to_http_exception(e)

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)  # type: ignore
        except Exception as e:
            oauth_to_http_exception(e)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    return sync_wrapper  # type: ignore
