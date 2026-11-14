"""
**File:** ``test_identity.py``
**Region:** ``tests/linked_service/test_identity``

Unit tests for AICIdentityLinkedService and AICIdentityLinkedServiceSettings.
"""

from __future__ import annotations

import uuid

from ds_protocol_http_py_lib.enums import AuthType

from ds_provider_aic_py_lib.enums import ResourceType
from ds_provider_aic_py_lib.linked_service.identity import (
    AICIdentityBearerAuthSettings,
    AICIdentityLinkedService,
    AICIdentityLinkedServiceSettings,
    AICIdentityOAuth2AuthSettings,
)


def test_settings_defaults() -> None:
    """AIC identity settings default to the production host and bearer login."""
    settings = AICIdentityLinkedServiceSettings()
    assert settings.host == "auth.grasp-daas.com"
    assert settings.auth_type == AuthType.BEARER
    assert settings.schema == "https"
    assert settings.oauth2 is None
    assert settings.bearer is None


def test_oauth2_and_bearer_defaults() -> None:
    """Token endpoints are the production defaults. No API resource is chosen."""
    oauth2 = AICIdentityOAuth2AuthSettings(client_id="client", client_secret="secret")
    bearer = AICIdentityBearerAuthSettings(username="user@example.com", password="secret")
    assert oauth2.token_endpoint == "https://auth.grasp-daas.com/oauth/token/"
    assert oauth2.scope == "openid read"
    assert oauth2.data is None
    assert bearer.token_endpoint == "https://auth.grasp-daas.com/auth/login/"
    assert bearer.username_key_name == "email"


def test_settings_custom_values() -> None:
    """Callers can point the same settings at another host and auth type."""
    oauth2 = AICIdentityOAuth2AuthSettings(client_id="client", client_secret="secret")
    settings = AICIdentityLinkedServiceSettings(
        host="auth-dev.grasp-daas.com",
        auth_type=AuthType.OAUTH2,
        schema="https",
        oauth2=oauth2,
    )
    assert settings.host == "auth-dev.grasp-daas.com"
    assert settings.auth_type == AuthType.OAUTH2
    assert settings.oauth2 == oauth2


def test_linked_service_type() -> None:
    """The linked service reports the AIC identity resource type."""
    service = AICIdentityLinkedService(
        id=uuid.uuid4(),
        name="aic-identity",
        version="v1.0.0",
        settings=AICIdentityLinkedServiceSettings(),
    )
    assert service.type == ResourceType.LINKED_SERVICE_IDENTITY
    assert service.type.value == "ds.resource.linked-service.aic-identity"
