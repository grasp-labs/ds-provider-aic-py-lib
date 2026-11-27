"""
**File:** ``gold.py``
**Region:** ``ds_provider_aic_py_lib/dataset/gold``

Read-only dataset for an AIC gold table served by the fetch API.

The settings hold the published definition from ``ds-pipeline-infra``.
This package does not own gold and does not write it.

``read()`` requires SQL and posts it to ``POST /query/``. Truncated pages
are followed inside that call. ``output`` is the full frame.
"""

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

import pandas as pd
from ds_common_logger_py_lib import Logger
from ds_common_serde_py_lib import Serializable
from ds_resource_plugin_py_lib.common.resource.dataset import DatasetSettings, DatasetStorageFormatType, TabularDataset
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ListError, ReadError
from ds_resource_plugin_py_lib.common.resource.errors import NotSupportedError, ResourceException
from ds_resource_plugin_py_lib.common.serde.deserialize import PandasDeserializer
from ds_resource_plugin_py_lib.common.serde.serialize import PandasSerializer

from ..enums import HistoryMode, Layer, PublishMode, ResourceType
from ..linked_service.identity import AICIdentityLinkedService
from ..serde.deserializer import FetchQueryDeserializer
from .utils.frame import concat
from .utils.listing import list_params
from .utils.sql import qualify, statement

logger = Logger.get_logger(__name__, package=True)

_FETCH_URL = "https://grasp-daas.com/api/fetch/v1"


@dataclass(kw_only=True)
class GoldReadSettings(Serializable):
    """SQL sent to fetch for ``read()``."""

    sql: str
    """One statement for this dataset. Name it ``gold``. Another dataset is rejected."""

    fresh: bool = False
    """Send ``Cache-Control: no-cache`` when true."""


@dataclass(kw_only=True)
class GoldListSettings(Serializable):
    """Scope for ``list()`` against ``GET /dataset/``."""

    names: list[str] | None = None
    """Dataset names. ``None`` lists everything the caller is granted."""

    layers: list[Layer] | None = None
    """Layers to include. ``None`` does not filter by layer."""

    limit: int = 100
    """Page size. Fetch accepts 1 to 500."""

    fresh: bool = False
    """Send ``Cache-Control: no-cache`` when true."""


@dataclass(kw_only=True)
class AICGoldDatasetSettings(DatasetSettings):
    """Published gold definition and the fetch scope for this dataset."""

    url: str = _FETCH_URL
    """Fetch API base URL."""

    publish_mode: PublishMode
    """How candidate rows mutate published gold state. Stored, not executed."""

    primary_key_fields: list[str]
    """Business key of the published dataset."""

    history_mode: HistoryMode
    """History strategy of the published dataset."""

    partition_keys: list[str]
    """Partition columns of the published dataset."""

    ordering_field: str | None = None
    """Duplicate-winner field of the published dataset."""

    delete_field: str | None = None
    """Delete-intent field of the published dataset."""

    read: GoldReadSettings | None = None
    """SQL for ``read()``. Required when reading."""

    list: GoldListSettings = field(default_factory=GoldListSettings)
    """Scope for ``list()``."""


AICGoldDatasetSettingsType = TypeVar("AICGoldDatasetSettingsType", bound=AICGoldDatasetSettings)
AICIdentityLinkedServiceType = TypeVar("AICIdentityLinkedServiceType", bound=AICIdentityLinkedService[Any])


@dataclass(kw_only=True)
class AICGoldDataset(
    TabularDataset[
        AICIdentityLinkedServiceType,
        AICGoldDatasetSettingsType,
        PandasSerializer,
        FetchQueryDeserializer,
    ],
    Generic[AICIdentityLinkedServiceType, AICGoldDatasetSettingsType],
):
    """Read-only gold dataset. Mutation methods are not supported."""

    linked_service: AICIdentityLinkedServiceType
    settings: AICGoldDatasetSettingsType

    serializer: PandasSerializer | None = None
    """Unused. Gold is read-only."""

    deserializer: FetchQueryDeserializer = field(default_factory=FetchQueryDeserializer)
    """Materializes one fetch query page."""

    @property
    def type(self) -> ResourceType:
        """Resource type discriminator."""
        return ResourceType.DATASET_GOLD

    @property
    def supports_checkpoint(self) -> bool:
        """A failed read keeps the next offset in ``checkpoint['pagination']``."""
        return True

    def read(self) -> None:
        """Post the required SQL and assign the full result to ``output``.

        Fetch stops a response at 100_000 rows or 8 MiB. This call follows
        truncated pages until the result is complete. Later pages use
        ``OFFSET``, so a result that can span more than one page needs
        ``ORDER BY`` to keep a stable row order. A failure keeps the pages
        already read in ``output`` and the next offset in
        ``checkpoint['pagination']``. A truncated page with no rows to
        continue from raises and leaves that offset in place.

        Raises:
            ReadError: SQL is missing, a quoted reference names another dataset, fetch rejects a page, or a truncated page
                cannot be continued.
        """
        if self.settings.read is None or not self.settings.read.sql.strip():
            raise ReadError(message="SQL is required.")

        sql = qualify(self.settings.read.sql.strip(), self.id)
        offset = 0
        saved = self.checkpoint.get("pagination")
        if isinstance(saved, dict):
            offset = int(saved.get("offset", 0) or 0)

        frames: list[pd.DataFrame] = []
        try:
            while True:
                body = self._query(statement(sql, offset))
                frames.append(self.deserializer(body))
                if not self.deserializer.get_next(body):
                    break
                cursor = self.deserializer.get_end_cursor(body, offset=offset)
                if cursor is None:
                    raise ReadError(message="Fetch truncated the result but returned no rows to continue from.")
                offset = int(cursor)
                self.checkpoint["pagination"] = {"offset": offset}
        except Exception as exc:
            self.output = concat(frames)
            if isinstance(exc, ReadError):
                raise
            raise ReadError(message=str(exc)) from exc

        self.output = concat(frames)
        self.checkpoint.pop("pagination", None)

    def list(self) -> None:
        """List granted datasets and assign one frame to ``output``.

        Raises:
            ListError: Fetch rejects a page or a page is not a dataset page.
        """
        frames: list[pd.DataFrame] = []
        offset = 0
        deserializer = PandasDeserializer(format=DatasetStorageFormatType.SEMI_STRUCTURED_JSON)
        while True:
            try:
                response = self.linked_service.connection.get(
                    url=f"{self.settings.url.rstrip('/')}/dataset/",
                    params=list_params(self.settings.list, offset),
                    headers=self._headers(self.settings.list.fresh),
                )
            except ResourceException as exc:
                raise ListError(message=exc.message, status_code=exc.status_code, details=exc.details) from exc

            body = response.json()
            rows = body.get("data") if isinstance(body, dict) else None
            page = body.get("page") if isinstance(body, dict) else None
            if not isinstance(rows, list) or not isinstance(page, dict):
                raise ListError(message="Fetch dataset list did not return a page.")

            frames.append(deserializer(rows) if rows else pd.DataFrame())
            if not page.get("has_next") or not rows:
                break
            offset += len(rows)

        self.output = concat(frames)

    def create(self) -> None:
        """Gold is owned by the platform."""
        raise NotSupportedError("Method create is not supported by AIC gold dataset.")

    def update(self) -> None:
        """Gold is owned by the platform."""
        raise NotSupportedError("Method update is not supported by AIC gold dataset.")

    def upsert(self) -> None:
        """Gold is owned by the platform."""
        raise NotSupportedError("Method upsert is not supported by AIC gold dataset.")

    def delete(self) -> None:
        """Gold is owned by the platform."""
        raise NotSupportedError("Method delete is not supported by AIC gold dataset.")

    def purge(self) -> None:
        """Gold is owned by the platform."""
        raise NotSupportedError("Method purge is not supported by AIC gold dataset.")

    def rename(self) -> None:
        """Gold is owned by the platform."""
        raise NotSupportedError("Method rename is not supported by AIC gold dataset.")

    def close(self) -> None:
        """Release the identity session."""
        self.linked_service.close()

    def _query(self, sql: str) -> dict[str, Any]:
        fresh = bool(self.settings.read and self.settings.read.fresh)
        try:
            response = self.linked_service.connection.post(
                url=f"{self.settings.url.rstrip('/')}/query/",
                json={"sql": sql},
                headers=self._headers(fresh),
            )
        except ResourceException as exc:
            raise ReadError(message=exc.message, status_code=exc.status_code, details=exc.details) from exc
        body = response.json()
        if not isinstance(body, dict):
            raise ReadError(message="Fetch returned a JSON value that is not an object.")
        return body

    def _headers(self, fresh: bool) -> dict[str, str]:
        headers = {"Accept-Encoding": "gzip"}
        if fresh:
            headers["Cache-Control"] = "no-cache"
        return headers
