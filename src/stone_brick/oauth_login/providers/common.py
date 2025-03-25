from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

OAuthProvider = Literal["google", "DUMMY"]


class OAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    auth_uri: str
    token_uri: str
    redirect_uri: str
    scopes: list[str] = Field(default_factory=lambda: [])


class ProviderError(Exception):
    provider: OAuthProvider

    def __init__(self, provider: OAuthProvider, *, status: int = 503, add_info: Any):
        super().__init__(f"Failed with provider {provider}", add_info)
        self.provider = provider
        self.status = status


class UserInfo(BaseModel):
    email: str
    name: str
    photo_url: str


class BaseOAuthLoginProvider(ABC):
    @abstractmethod
    def get_authorization_url(self, state: str) -> str: ...

    @abstractmethod
    async def get_user_info(self, code: str) -> UserInfo: ...
