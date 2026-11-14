"""
**File:** ``deserializer.py``
**Region:** ``ds_provider_aic_py_lib/serde``

Deserialize a fetch query result into a dataframe.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import pandas as pd
import pyarrow as pa
from ds_common_serde_py_lib.errors import DeserializationError
from ds_resource_plugin_py_lib.common.serde.deserialize.base import DataDeserializer

_DECIMAL_RE = re.compile(r"^DECIMAL\((?P<precision>\d+)\s*,\s*(?P<scale>\d+)\)$")
_FLOAT_TOKENS = {
    "NAN": float("nan"),
    "INFINITY": float("inf"),
    "-INFINITY": float("-inf"),
}
_STRINGS = frozenset({"VARCHAR", "UUID", "BLOB", "INTERVAL", "HUGEINT", "UHUGEINT", "CHAR", "TEXT", "STRING"})
_INTEGERS = {
    "TINYINT": pa.int8(),
    "SMALLINT": pa.int16(),
    "INTEGER": pa.int32(),
    "BIGINT": pa.int64(),
    "UTINYINT": pa.uint8(),
    "USMALLINT": pa.uint16(),
    "UINTEGER": pa.uint32(),
    "UBIGINT": pa.uint64(),
}
_FLOATS = {
    "FLOAT": pa.float32(),
    "DOUBLE": pa.float64(),
    "REAL": pa.float32(),
}


class FetchQueryDeserializer(DataDeserializer):
    """Turn one fetch ``QueryResult`` into a pandas frame."""

    def __call__(self, value: Any, **_kwargs: Any) -> pd.DataFrame:
        """Deserialize a query body.

        Args:
            value: JSON object, or a JSON string or bytes body.
            **_kwargs: Unused. Present for the deserializer contract.

        Returns:
            A frame whose columns follow ``columns`` and use arrow dtypes.

        Raises:
            DeserializationError: The body is not a rectangular query result.
        """
        payload = _payload(value)
        columns = _columns(payload.get("columns"))
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise DeserializationError(message="Fetch query result is missing rows.", details={"field": "rows"})

        names = [column["name"] for column in columns]
        width = len(names)
        series: list[pd.Series[Any]] = []
        for index, column in enumerate(columns):
            values = [_cell(row, index, width) for row in rows]
            series.append(_series(column["name"], column["type"], values))
        if not series:
            return pd.DataFrame(columns=names)
        return pd.concat(series, axis=1)

    def get_next(self, value: Any, **_kwargs: Any) -> bool:  # type: ignore[override]
        """Return whether fetch truncated this page."""
        return bool(_payload(value).get("truncated"))

    def get_end_cursor(self, value: Any, **kwargs: Any) -> str | None:  # type: ignore[override]
        """Return the next row offset when this page has rows.

        Args:
            value: Query body.
            **kwargs: ``offset`` is the offset this page was read from.

        Returns:
            The absolute offset of the next page, or ``None`` when the page is empty.
        """
        count = _payload(value).get("row_count")
        if not isinstance(count, int) or count < 1:
            return None
        return str(int(kwargs.get("offset", 0)) + count)


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        loaded = json.loads(value)
        if isinstance(loaded, dict):
            return loaded
    raise DeserializationError(message="Fetch query result is not a JSON object.")


def _columns(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise DeserializationError(message="Fetch query result is missing columns.", details={"field": "columns"})
    columns: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("type"), str):
            raise DeserializationError(message="Fetch column is missing name or type.", details={"column": item})
        name = item["name"]
        if name in seen:
            raise DeserializationError(message="Fetch query result repeats a column name.", details={"column": name})
        seen.add(name)
        columns.append({"name": name, "type": item["type"]})
    return columns


def _cell(row: Any, index: int, width: int) -> Any:
    if not isinstance(row, list) or len(row) != width:
        raise DeserializationError(message="Fetch query row does not match the column list.")
    return row[index]


def _series(name: str, duckdb_type: str, values: list[Any]) -> pd.Series[Any]:
    arrow_type = _arrow_type(duckdb_type)
    if arrow_type is None:
        return pd.Series(values, dtype="object", name=name)
    if pa.types.is_floating(arrow_type):
        values = [_float_token(value) for value in values]
    elif pa.types.is_decimal(arrow_type):
        values = [None if value is None else Decimal(str(value)) for value in values]
    elif pa.types.is_temporal(arrow_type):
        values = [_temporal(value, arrow_type) for value in values]
    try:
        array = pa.array(values, type=arrow_type)
    except (pa.ArrowInvalid, pa.ArrowTypeError, ValueError, OverflowError) as exc:
        raise DeserializationError(
            message=f"Column '{name}' cannot be cast to {duckdb_type}.",
            details={"column": name, "type": duckdb_type, "error": str(exc)},
        ) from exc
    return pd.Series(array, dtype=pd.ArrowDtype(arrow_type), name=name)


def _temporal(value: Any, arrow_type: pa.DataType) -> Any:
    if value is None:
        return None
    if pa.types.is_date(arrow_type):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))
    if pa.types.is_time(arrow_type):
        if isinstance(value, time):
            return value
        return time.fromisoformat(str(value))
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00")) if not isinstance(value, datetime) else value
    if arrow_type.tz is not None:
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _float_token(value: Any) -> Any:
    if isinstance(value, str) and value.upper() in _FLOAT_TOKENS:
        return _FLOAT_TOKENS[value.upper()]
    return value


def _arrow_type(duckdb_type: str) -> pa.DataType | None:
    normalized = " ".join(duckdb_type.strip().upper().split())
    if normalized.startswith("DECIMAL"):
        return _decimal_type(normalized)
    if normalized.startswith(("LIST", "ARRAY", "STRUCT", "MAP")):
        return None
    type_name = normalized.split("(", 1)[0].strip()
    if type_name in _STRINGS or type_name == "ENUM" or normalized.startswith("ENUM"):
        return pa.large_string()
    if type_name == "BOOLEAN":
        return pa.bool_()
    if type_name == "DATE":
        return pa.date32()
    if type_name == "TIME":
        return pa.time64("us")
    if type_name in {"TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE"}:
        return pa.timestamp("us", tz="UTC")
    if type_name == "TIMESTAMP":
        return pa.timestamp("us")
    if type_name in _INTEGERS:
        return _INTEGERS[type_name]
    if type_name in _FLOATS:
        return _FLOATS[type_name]
    return None


def _decimal_type(normalized: str) -> pa.DataType:
    matched = _DECIMAL_RE.match(normalized)
    if matched is None:
        return pa.large_string()
    precision = int(matched.group("precision"))
    scale = int(matched.group("scale"))
    if precision < 1 or scale < 0 or scale > precision or precision > 76:
        return pa.large_string()
    if precision > 38:
        return pa.decimal256(precision, scale)
    return pa.decimal128(precision, scale)
