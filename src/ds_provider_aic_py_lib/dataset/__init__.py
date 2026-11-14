"""
**File:** ``__init__.py``
**Region:** ``ds_provider_aic_py_lib/dataset``

AIC gold dataset.

Example:
    >>> dataset = AICGoldDataset(
    ...     id=uuid.uuid4(),
    ...     name="employees",
    ...     version="1.0.0",
    ...     linked_service=linked_service,
    ...     settings=AICGoldDatasetSettings(
    ...         publish_mode=PublishMode.UPSERT,
    ...         primary_key_fields=["employee_id"],
    ...         history_mode=HistoryMode.SCD2,
    ...         partition_keys=[],
    ...         read=GoldReadSettings(sql="SELECT * FROM gold"),
    ...     ),
    ... )
    >>> dataset.read()
    >>> dataset.output
"""

from .gold import AICGoldDataset, AICGoldDatasetSettings, GoldListSettings, GoldReadSettings

__all__ = [
    "AICGoldDataset",
    "AICGoldDatasetSettings",
    "GoldListSettings",
    "GoldReadSettings",
]
