"""
**File:** ``listing.py``
**Region:** ``ds_provider_aic_py_lib/dataset/utils/listing``

Query parameters for one page of ``GET /dataset/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..gold import GoldListSettings


def list_params(listing: GoldListSettings, offset: int) -> list[tuple[str, str | int]]:
    """Build the repeated query parameters for one dataset page."""
    params: list[tuple[str, str | int]] = [("limit", listing.limit), ("offset", offset)]
    for name in listing.names or []:
        params.append(("name", name))
    for layer in listing.layers or []:
        params.append(("layer", layer.value))
    return params
