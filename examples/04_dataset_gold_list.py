"""
**File:** ``04_dataset_gold_list.py``
**Region:** ``examples/04_dataset_gold_list``

Example 04: List the fetch datasets the caller is granted.

Run from the repository root::

    uv run --extra dev python examples/04_dataset_gold_list.py
"""

from __future__ import annotations

import logging
import os
from uuid import uuid4

from dotenv import load_dotenv
from ds_common_logger_py_lib import Logger
from ds_protocol_http_py_lib.enums import AuthType

from ds_provider_aic_py_lib.dataset.gold import AICGoldDataset, AICGoldDatasetSettings, GoldListSettings
from ds_provider_aic_py_lib.enums import HistoryMode, Layer, PublishMode
from ds_provider_aic_py_lib.linked_service.identity import (
    AICIdentityLinkedService,
    AICIdentityLinkedServiceSettings,
    AICIdentityOAuth2AuthSettings,
)

load_dotenv()
Logger.configure(level=logging.INFO)
logger = Logger.get_logger(__name__)


def main() -> None:
    """List granted datasets."""
    linked_service = AICIdentityLinkedService(
        id=uuid4(),
        name="example-aic-identity",
        version="v1.0.0",
        settings=AICIdentityLinkedServiceSettings(
            auth_type=AuthType.OAUTH2,
            oauth2=AICIdentityOAuth2AuthSettings(
                client_id=os.environ["AIC_CLIENT_ID"],
                client_secret=os.environ["AIC_CLIENT_SECRET"],
            ),
        ),
    )
    dataset = AICGoldDataset(
        id=uuid4(),
        name="example-aic-gold",
        version="v1.0.0",
        linked_service=linked_service,
        settings=AICGoldDatasetSettings(
            publish_mode=PublishMode.UPSERT,
            primary_key_fields=["id"],
            history_mode=HistoryMode.NONE,
            partition_keys=[],
            list=GoldListSettings(layers=[Layer.GOLD]),
        ),
    )

    try:
        linked_service.connect()
        dataset.list()
        logger.info("Datasets:\n%s", dataset.output)
    finally:
        dataset.close()


if __name__ == "__main__":
    main()
