"""
**File:** ``enums.py``
**Region:** ``ds_provider_aic_py_lib/enums``

Constants for the AIC provider.

Example:
    >>> ResourceType.DATASET_GOLD
    'ds.resource.dataset.aic-gold'
"""

from enum import StrEnum


class ResourceType(StrEnum):
    """Resource type identifiers for the AIC provider."""

    LINKED_SERVICE_IDENTITY = "ds.resource.linked-service.aic-identity"
    DATASET_GOLD = "ds.resource.dataset.aic-gold"


class PublishMode(StrEnum):
    """How candidate rows mutate published gold state.

    Declared by the gold dataset definition in ``ds-pipeline-infra``.
    This provider stores the value and does not publish rows.
    """

    UPSERT = "upsert"
    REPLACE = "replace"


class HistoryMode(StrEnum):
    """History strategy declared for a published gold dataset."""

    SCD2 = "scd2"
    NONE = "none"


class Layer(StrEnum):
    """Fetch dataset layer accepted by ``GET /dataset/``."""

    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
