from functools import lru_cache
from typing import Any, Type, TypeVar

from pydantic import TypeAdapter

T = TypeVar("T")


@lru_cache()
def get_type_adapter(t: Type[T]) -> TypeAdapter[T]:
    return TypeAdapter(t)


def cast_type(t: Type[T], data: Any) -> T:
    type_adapter = get_type_adapter(t)
    # type ignore due to lru_cache
    return type_adapter.validate_python(data)  # type: ignore
