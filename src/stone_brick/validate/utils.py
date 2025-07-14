import os
import re
from functools import lru_cache
from typing import Annotated, Any, Type, TypeAlias, TypeVar

from pydantic import BeforeValidator, TypeAdapter

T = TypeVar("T")


@lru_cache()
def get_type_adapter(t: Type[T]) -> TypeAdapter[T]:
    return TypeAdapter(t)


def cast_type(t: Type[T], data: Any) -> T:
    type_adapter = get_type_adapter(t)
    # type ignore due to lru_cache
    return type_adapter.validate_python(data)  # type: ignore


def _get_str_from_env(k: str) -> str:
    # Check if the entire string matches ${VALUE} pattern
    pattern = r'^\$\{([^}]+)\}$'
    match = re.match(pattern, k)
    if match:
        env_var_name = match.group(1)
        v = os.getenv(env_var_name)
        if v is None:
            raise ValueError(f"Environment variable {env_var_name} is not set")
        else:
            return v
    else:
        raise ValueError("This field must be the pattern of ${VALUE}")
    
T = TypeVar("T")
EnvVar: TypeAlias = Annotated[T, BeforeValidator(_get_str_from_env)]