"""
**File:** ``02_linked_service_password.py``
**Region:** ``examples/02_linked_service_password``

Example 02: Sign in to AIC identity with username and password.

``AIC_USERNAME`` is the account email. The HTTP protocol posts it to
``/auth/login/`` and stores the bearer token.

Run from the repository root::

    uv run --extra dev python examples/02_linked_service_password.py
"""

from __future__ import annotations

import logging
import os
from uuid import uuid4

from dotenv import load_dotenv
from ds_common_logger_py_lib import Logger

from ds_provider_aic_py_lib.linked_service.identity import (
    AICIdentityBearerAuthSettings,
    AICIdentityLinkedService,
    AICIdentityLinkedServiceSettings,
)

load_dotenv()
Logger.configure(level=logging.INFO)
logger = Logger.get_logger(__name__)


def main() -> None:
    """Connect with username and password and check the identity host."""
    linked_service = AICIdentityLinkedService(
        id=uuid4(),
        name="example-aic-identity",
        version="v1.0.0",
        settings=AICIdentityLinkedServiceSettings(
            bearer=AICIdentityBearerAuthSettings(
                username=os.environ["AIC_USERNAME"],
                password=os.environ["AIC_PASSWORD"],
            ),
        ),
    )

    try:
        linked_service.connect()
        ok, message = linked_service.test_connection()
        logger.info("Connection test result: ok=%s message=%s", ok, message)
    finally:
        linked_service.close()


if __name__ == "__main__":
    main()
