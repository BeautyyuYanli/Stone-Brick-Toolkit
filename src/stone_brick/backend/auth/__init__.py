import logging
from typing import Awaitable, Callable, Tuple, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

from stone_brick.backend.ctx import Ctx
from stone_brick.encryptlib import JWT
from stone_brick.oauth_login import (
    GoogleOAuthLoginProvider,
    OAuthGoogleConfig,
    OAuthProvider,
)
from stone_brick.oauth_login.providers.common import UserInfo

logger = logging.getLogger(__name__)


class StatePayload(BaseModel):
    provider: OAuthProvider
    redirect_uri: str
    nonce: str = Field(default_factory=lambda: str(uuid4()))


class LoginFinishRequest(BaseModel):
    state: str
    code: str


def get_google_provider(ctx: Ctx, redirect_uri: str):
    if ctx.config.oauth_login.google is None:
        raise ValueError("Google OAuth login is not configured")
    return GoogleOAuthLoginProvider(
        config=OAuthGoogleConfig(
            client_id=ctx.config.oauth_login.google.client_id,
            client_secret=ctx.config.oauth_login.google.client_secret,
            project_id=ctx.config.oauth_login.google.project_id,
            redirect_uri=redirect_uri or "",
        ),
    )


async def login_start(
    ctx: Ctx,
    provider: OAuthProvider,
    redirect_uri: str,
) -> Tuple[str, str]:
    """Initialize the login flow. Returns the authorization URL and the state.
    The state should be stored in the client, and the client should verify it
    when receiving the callback from auth provider.
    """

    state = JWT[StatePayload](
        payload=StatePayload(
            provider=provider,
            redirect_uri=redirect_uri,
        ),
    ).encode(ctx.config.key_256)
    match provider:
        case "google":
            return (
                get_google_provider(
                    ctx, redirect_uri=redirect_uri
                ).get_authorization_url(state=state),
                state,
            )
        case _:
            raise ValueError(f"Unsupported provider: {provider}")


T = TypeVar("T")


async def login_finish(
    ctx: Ctx,
    data: LoginFinishRequest,
    get_user: Callable[[Ctx, UserInfo], Awaitable[T]],
):
    """
    Before calling this function to get the user info, the client should firstly verify the state.
    """
    try:
        plain_state = JWT[StatePayload].decode(
            key=ctx.config.key_256,
            encoded=data.state,
        )
    except Exception as e:
        raise ValueError("Invalid state when finishing login") from e

    match plain_state.payload.provider:
        case "google":
            user_info: UserInfo = await get_google_provider(
                ctx, redirect_uri=plain_state.payload.redirect_uri
            ).get_user_info(data.code)
        case _:
            raise ValueError(f"Unsupported provider: {plain_state.payload.provider}")

    return await get_user(ctx, user_info)
