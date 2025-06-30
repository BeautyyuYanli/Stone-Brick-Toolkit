from typing import Generic, Optional, Sequence, TypeVar, Union

from jwt import decode, encode
from pydantic import BaseModel
from typing_extensions import Self

T = TypeVar("T")


class JWT(BaseModel, Generic[T]):
    payload: T
    iss: Optional[str] = None  # Issuer
    sub: Optional[str] = None  # Subject
    aud: Optional[Union[str, Sequence[str]]] = None  # Audience
    exp: Optional[int] = None  # Expiration Time
    nbf: Optional[int] = None  # Not Before
    iat: Optional[int] = None  # Issued At
    jti: Optional[str] = None  # JWT ID

    @classmethod
    def decode(
        cls,
        key: bytes,
        encoded: str,
        algorithm: Sequence[str] = ("HS256",),
    ) -> Self:
        decoded = decode(encoded, key, algorithms=algorithm)
        return cls.model_validate(decoded)

    def encode(self, key: bytes, algorithm: str = "HS256") -> str:
        return encode(
            self.model_dump(mode="json", exclude_none=True), key, algorithm=algorithm
        )
