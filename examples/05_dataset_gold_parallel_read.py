"""
**File:** ``05_dataset_gold_parallel_read.py``
**Region:** ``examples/05_dataset_gold_parallel_read``

Example 05: Read one gold dataset from many threads at once.

One linked service signs in. Each thread has its own dataset on that
connection and calls ``read()``. The threads start together.
``fresh`` is off, so fetch may serve a cached page. Each line is that
reader's outcome.

The statement is ``LIMIT 10``, so the overlap is the requests. Credentials
come from ``.env``. The dataset, the reader count, and the SQL are set below.

Run from the repository root::

    uv run --extra dev python examples/05_dataset_gold_parallel_read.py
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

from dotenv import load_dotenv
from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ReadError

from ds_provider_aic_py_lib.dataset.gold import AICGoldDataset, AICGoldDatasetSettings, GoldReadSettings
from ds_provider_aic_py_lib.enums import HistoryMode, PublishMode
from ds_provider_aic_py_lib.linked_service.identity import (
    AICIdentityBearerAuthSettings,
    AICIdentityLinkedService,
    AICIdentityLinkedServiceSettings,
)

load_dotenv()
Logger.configure(level=logging.INFO)
logger = Logger.get_logger(__name__)

READERS = 60
DATASET_ID = UUID("<>")
SQL = "SELECT * FROM gold LIMIT 10"


def _dataset(linked_service: AICIdentityLinkedService, index: int) -> AICGoldDataset:
    """Build one dataset for this reader on the shared connection."""
    return AICGoldDataset(
        id=DATASET_ID,
        name=f"example-aic-gold-{index}",
        version="v1.0.0",
        linked_service=linked_service,
        settings=AICGoldDatasetSettings(
            publish_mode=PublishMode.UPSERT,
            primary_key_fields=["id"],
            history_mode=HistoryMode.NONE,
            partition_keys=[],
            read=GoldReadSettings(sql=SQL, fresh=False),
        ),
    )


def _read(index: int, dataset: AICGoldDataset, barrier: threading.Barrier) -> None:
    """Wait for the other readers, then read and log the outcome."""
    barrier.wait()
    started = time.perf_counter()
    try:
        dataset.read()
    except ReadError as exc:
        logger.info(
            "reader=%s seconds=%.2f status=%s message=%s",
            index,
            time.perf_counter() - started,
            exc.status_code,
            exc.message,
        )
        return
    logger.info(
        "reader=%s seconds=%.2f rows=%s",
        index,
        time.perf_counter() - started,
        len(dataset.output),
    )


def main() -> None:
    """Sign in once, then read in parallel."""
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
    datasets = [_dataset(linked_service, index) for index in range(READERS)]
    try:
        linked_service.connect()
        barrier = threading.Barrier(READERS)
        with ThreadPoolExecutor(max_workers=READERS) as pool:
            futures = [pool.submit(_read, index, dataset, barrier) for index, dataset in enumerate(datasets)]
            for future in futures:
                future.result()
    finally:
        linked_service.close()


if __name__ == "__main__":
    main()
