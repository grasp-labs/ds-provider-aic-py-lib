"""
**File:** ``frame.py``
**Region:** ``ds_provider_aic_py_lib/dataset/utils/frame``

Combine fetched pages into one frame.
"""

import pandas as pd


def concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate page frames, or return an empty frame when none were fetched."""
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
