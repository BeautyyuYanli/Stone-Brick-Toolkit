import logging
from dataclasses import field
from typing import Union, cast

import anyio
import anyio.to_thread
from google.auth.external_account_authorized_user import (
    Credentials as ExternalAccountCredentials,
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from pydantic import BaseModel

from stone_brick.oauth_login.providers.common import (
    BaseOAuthLoginProvider,
    OAuthConfig,
    ProviderError,
    UserInfo,
)

logger = logging.getLogger(__name__)

GoogleCredentials = Union[Credentials, ExternalAccountCredentials]


class OAuthGoogleConfig(OAuthConfig):
    project_id: str
    scopes: list[str] = field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid",
        ]
    )
    auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    token_uri: str = "https://oauth2.googleapis.com/token"


def _new_flow(config: OAuthGoogleConfig):
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "project_id": config.project_id,
                "auth_uri": config.auth_uri,
                "token_uri": config.token_uri,
            }
        },
        scopes=config.scopes,
        redirect_uri=config.redirect_uri,
    )
    return flow


def flow_start_google(config: OAuthGoogleConfig, state: str):
    """Non-blocking OAuth authorization flow start"""

    flow = _new_flow(config)

    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    if not isinstance(url, str):
        raise ProviderError(
            "google",
            add_info="Failed to get authorization URL from Google",
        )
    return url


async def flow_finish_google(
    config: OAuthGoogleConfig,
    code: str,
) -> GoogleCredentials:
    """OAuth authorization flow finish"""
    flow = _new_flow(config)
    try:
        await anyio.to_thread.run_sync(lambda: flow.fetch_token(code=code))
    except Exception as e:
        if isinstance(e, OAuth2Error):
            raise ProviderError(
                "google",
                status=400,
                add_info="Failed to fetch token by code with an OAuth2 error",
            ) from e
        else:
            raise ProviderError(
                "google",
                add_info="Failed to fetch token by code",
            ) from e

    return flow.credentials


async def get_google_user_info(credentials: GoogleCredentials):
    """OAuth authorization flow get user info"""
    service = build("people", "v1", credentials=credentials)
    try:
        results = await anyio.to_thread.run_sync(
            lambda: service.people()
            .get(
                resourceName="people/me",
                personFields="emailAddresses,names,photos",
            )
            .execute()
        )
    except Exception as e:
        raise ProviderError(
            "google",
            add_info="Failed to get user info",
        ) from e
    else:
        try:
            email = results["emailAddresses"][0]["value"]
            name = results["names"][0]["displayName"]
            photo_url = results["photos"][0]["url"]
        except (KeyError, IndexError) as e:
            raise ProviderError(
                "google",
                add_info="Some user info fields are missing",
            ) from e
    for val_field in (email, name, photo_url):
        if not isinstance(val_field, str):
            raise ProviderError(
                "google",
                add_info=(
                    "Some user info fields are not strings",
                    val_field,
                    type(val_field),
                ),
            )
    return cast(str, email), cast(str, name), cast(str, photo_url)


class GoogleOAuthLoginProvider(BaseOAuthLoginProvider, BaseModel):
    config: OAuthGoogleConfig

    def get_authorization_url(self, state: str) -> str:
        return flow_start_google(self.config, state)

    async def get_user_info(self, code: str) -> UserInfo:
        credentials = await flow_finish_google(self.config, code)
        email, name, photo_url = await get_google_user_info(credentials)
        return UserInfo(email=email, name=name, photo_url=photo_url)
