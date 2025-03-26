from time import time
from typing import Annotated, Tuple
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Response

from stone_brick.backend.auth import (
    LoginFinishRequest,
    login_finish,
    login_start,
)
from stone_brick.backend.ctx import Ctx, get_ctx
from stone_brick.backend.tables.user import create_user_if_not_exists
from stone_brick.encryptlib import JWT
from stone_brick.oauth_login import OAuthProvider, oauth_handle_exceptions

router = APIRouter(prefix="/login")


@router.get("/")
@oauth_handle_exceptions
async def flow_start(
    ctx: Annotated[Ctx, Depends(get_ctx)],
    provider: OAuthProvider,
    redirect_uri: str,
) -> Tuple[str, str]:
    return await login_start(ctx, provider, redirect_uri)


@router.post("/finish")
@oauth_handle_exceptions
async def flow_finish_sessionless(
    response: Response,
    ctx: Annotated[Ctx, Depends(get_ctx)],
    data: Annotated[LoginFinishRequest, Body()],
):
    user = await login_finish(ctx, data, create_user_if_not_exists)
    nbf = int(time())
    exp = nbf + int(ctx.config.oauth_login.sessionless_timeout)
    token = JWT[UUID](
        payload=user.id,
        nbf=nbf,
        exp=exp,
    ).encode(ctx.config.key_256)
    set_token_cookie(ctx, response, ctx.config.cookie_token, token)
    return user, exp


def get_second_domain(url: str) -> str:
    front_host = urlparse(url).netloc
    if ":" in front_host:  # Remove port if present
        front_host = front_host.split(":")[0]
    second_domain = "." + ".".join(front_host.split(".")[-2:])
    return second_domain


def set_token_cookie(ctx: Ctx, response: Response, key: str, value: str):
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=not ctx.debug,
        samesite="strict",
        domain=get_second_domain(ctx.config.domain) if not ctx.debug else ".",
    )
