from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from fastapi import FastAPI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio.engine import AsyncEngine

T = TypeVar("T")


class GoogleOAuthLoginConfig(BaseModel):
    client_id: str
    client_secret: str
    project_id: str


class OAuthLoginConfig(BaseModel):
    flow_timeout: float = 3 * 60
    sessionless_timeout: float = 3600 * 24 * 30
    google: Optional[GoogleOAuthLoginConfig] = None


class Config(BaseModel):
    domain: str
    front_url: str
    key_256: bytes
    cookie_prefix: str
    oauth_login: OAuthLoginConfig = Field(default_factory=OAuthLoginConfig)

    @property
    def cookie_token(self) -> str:
        return f"{self.cookie_prefix}_token"


@dataclass
class Resource:
    db: AsyncEngine
    fastapi: FastAPI


@dataclass
class Ctx(Generic[T]):
    debug: bool
    deps: T
    config: Config
    resource: Resource


_global_ctx: Ctx | None = None


def get_ctx() -> Ctx:
    if _global_ctx is None:
        raise RuntimeError("Ctx not initialized")
    return _global_ctx


def set_ctx(ctx: Ctx):
    global _global_ctx  # noqa: PLW0603
    _global_ctx = ctx
