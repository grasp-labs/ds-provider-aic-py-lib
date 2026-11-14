"""
**File**: `__init__.py`
**Region**: `ds_provider_aic_py_lib.linked_service`

AIC identity linked service.

Example:
    >>> linked_service = AICIdentityLinkedService(
    ...     id=uuid.uuid4(),
    ...     name="aic-identity",
    ...     version="1.0.0",
    ...     settings=AICIdentityLinkedServiceSettings(
    ...         auth_type=AuthType.BEARER,
    ...         bearer=AICIdentityBearerAuthSettings(
    ...             username="user@example.com",
    ...             password="pass",
    ...         ),
    ...     ),
    ... )
    >>> linked_service.connect()
"""

from .identity import (
    AICIdentityBearerAuthSettings,
    AICIdentityLinkedService,
    AICIdentityLinkedServiceSettings,
    AICIdentityOAuth2AuthSettings,
)

__all__ = [
    "AICIdentityBearerAuthSettings",
    "AICIdentityLinkedService",
    "AICIdentityLinkedServiceSettings",
    "AICIdentityOAuth2AuthSettings",
]
