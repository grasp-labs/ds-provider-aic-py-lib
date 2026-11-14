"""
**File:** ``03_dataset_gold_read.py``
**Region:** ``examples/03_dataset_gold_read``

Example 03: Read an AIC gold dataset.

``read()`` follows truncated pages and leaves the full frame on
``output``. Credentials come from ``.env``. The dataset and SQL are
set below.

Run from the repository root::

    uv run --extra dev python examples/03_dataset_gold_read.py
"""

from __future__ import annotations

import logging
import os
from uuid import UUID, uuid4

from dotenv import load_dotenv
from ds_common_logger_py_lib import Logger

from ds_provider_aic_py_lib.dataset.gold import AICGoldDataset, AICGoldDatasetSettings, GoldReadSettings
from ds_provider_aic_py_lib.enums import HistoryMode, PublishMode
from ds_provider_aic_py_lib.linked_service.identity import (
    AICIdentityLinkedService,
    AICIdentityLinkedServiceSettings,
    AICIdentityBearerAuthSettings,
)

load_dotenv()
Logger.configure(level=logging.DEBUG)
logger = Logger.get_logger(__name__)

DATASET_ID = UUID("<>")


def main() -> None:
    """Read gold."""
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
    dataset = AICGoldDataset(
        id=DATASET_ID,
        name="example-aic-gold",
        version="v1.0.0",
        linked_service=linked_service,
        settings=AICGoldDatasetSettings(
            publish_mode=PublishMode.UPSERT,
            primary_key_fields=["id"],
            history_mode=HistoryMode.NONE,
            partition_keys=[],
            read=GoldReadSettings(sql="SELECT source_id, account_name, balance FROM gold"),
        ),
    )

    try:
        linked_service.connect()
        dataset.read()
        logger.info("Rows=%s", len(dataset.output))
        logger.info("Dtypes:\n%s", dataset.output.dtypes)
        print(dataset.output)
    finally:
        dataset.close()


if __name__ == "__main__":
    main()
