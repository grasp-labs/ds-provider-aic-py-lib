"""
**File**: ``identity.py``
**Region**: ``ds_provider_aic_py_lib/linked_service/identity``

Linked service for the AIC identity server.

Sign-in is the HTTP protocol. This module only sets the AIC defaults.
"""

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from ds_protocol_http_py_lib.enums import AuthType
from ds_protocol_http_py_lib.linked_service.http import (
    BearerAuthSettings,
    HttpLinkedService,
    HttpLinkedServiceSettings,
    OAuth2AuthSettings,
)

from ..enums import ResourceType


@dataclass(kw_only=True)
class AICIdentityOAuth2AuthSettings(OAuth2AuthSettings):
    """
    OAuth2 client-credentials settings for the AIC identity server.

    Attributes:
        token_endpoint: The URL to obtain the OAuth2 token.
        scope: Scopes sent on the token request.
    """

    token_endpoint: str = field(default="https://auth.grasp-daas.com/oauth/token/")
    """The URL to obtain the OAuth2 token. Default is 'https://auth.grasp-daas.com/oauth/token/'"""

    scope: str | None = "openid read"
    """OAuth2 scope. Default is 'openid read'."""


@dataclass(kw_only=True)
class AICIdentityBearerAuthSettings(BearerAuthSettings):
    """
    Username and password settings for the AIC identity server.

    ``username`` is the account email. The HTTP protocol posts it to
    ``token_endpoint`` and stores the returned bearer token.

    Attributes:
        token_endpoint: The URL to obtain the bearer token.
    """

    token_endpoint: str = field(default="https://auth.grasp-daas.com/auth/login/")
    """The URL to obtain the bearer token. Default is 'https://auth.grasp-daas.com/auth/login/'"""


@dataclass(kw_only=True)
class AICIdentityLinkedServiceSettings(HttpLinkedServiceSettings):
    """
    Settings required to connect to the AIC identity server.

    Attributes:
        host: AIC identity host.
        auth_type: Bearer (username/password) or OAuth2 (client credentials).
        schema: The schema to use for the connection (e.g., "https").
        oauth2: OAuth2 authentication settings (if auth_type is OAUTH2).
        bearer: Username and password settings (if auth_type is BEARER).
    """

    host: str = field(default="auth.grasp-daas.com")
    """AIC identity host. Default is 'auth.grasp-daas.com'."""

    auth_type: AuthType = field(default=AuthType.BEARER)
    """The type of authentication to use. Default is BEARER."""

    schema: str = field(default="https")
    """The schema to use for the connection. Default is 'https'."""

    oauth2: AICIdentityOAuth2AuthSettings | None = None
    """OAuth2 authentication settings (if auth_type is OAUTH2)."""

    bearer: AICIdentityBearerAuthSettings | None = None
    """Username and password settings (if auth_type is BEARER)."""


AICIdentityLinkedServiceSettingsType = TypeVar(
    "AICIdentityLinkedServiceSettingsType",
    bound=AICIdentityLinkedServiceSettings,
)


@dataclass(kw_only=True)
class AICIdentityLinkedService(
    HttpLinkedService[AICIdentityLinkedServiceSettingsType],
    Generic[AICIdentityLinkedServiceSettingsType],
):
    """
    Linked service for the AIC identity server.
    """

    settings: AICIdentityLinkedServiceSettingsType

    @property
    def type(self) -> ResourceType:  # type: ignore[override]
        """
        The type of the linked service.

        Returns:
            ResourceType: The type of the linked service.
        """
        return ResourceType.LINKED_SERVICE_IDENTITY
