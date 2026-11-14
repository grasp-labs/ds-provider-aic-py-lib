"""
**File:** ``test_deserializer.py``
**Region:** ``tests/serde/test_deserializer``

Unit tests for FetchQueryDeserializer.
"""

from __future__ import annotations

import pyarrow as pa
import pytest
from ds_common_serde_py_lib.errors import DeserializationError

from ds_provider_aic_py_lib.serde.deserializer import FetchQueryDeserializer


def _frame(columns: list[dict[str, str]], rows: list[list[object]]) -> object:
    return FetchQueryDeserializer()(
        {"columns": columns, "rows": rows, "row_count": len(rows), "truncated": False},
    )


def test_query_result_uses_arrow_dtypes() -> None:
    """DuckDB types on the query result become arrow-backed columns."""
    frame = _frame(
        [
            {"name": "name", "type": "VARCHAR"},
            {"name": "n", "type": "BIGINT"},
            {"name": "flag", "type": "BOOLEAN"},
            {"name": "amount", "type": "DECIMAL(18,2)"},
            {"name": "score", "type": "DOUBLE"},
        ],
        [["engineering", 1, True, "1.50", "Infinity"]],
    )
    assert frame["name"].iloc[0] == "engineering"  # type: ignore[index]
    assert frame["n"].iloc[0] == 1  # type: ignore[index]
    assert frame["flag"].iloc[0] is True  # type: ignore[index]
    assert str(frame["amount"].dtype) == "decimal128(18, 2)[pyarrow]"  # type: ignore[index]
    assert frame["score"].iloc[0] == pytest.approx(float("inf"))  # type: ignore[index]
    assert frame["n"].dtype.pyarrow_dtype == pa.int64()  # type: ignore[attr-defined]


def test_temporal_string_enum_and_wide_decimal_types() -> None:
    """The remaining DuckDB scalars map onto arrow, and unknown types stay objects."""
    frame = _frame(
        [
            {"name": "day", "type": "DATE"},
            {"name": "clock", "type": "TIME"},
            {"name": "stamp", "type": "TIMESTAMP"},
            {"name": "when", "type": "TIMESTAMP WITH TIME ZONE"},
            {"name": "kind", "type": "ENUM"},
            {"name": "wide", "type": "DECIMAL(40, 2)"},
            {"name": "loose", "type": "DECIMAL"},
            {"name": "geom", "type": "GEOMETRY"},
            {"name": "score", "type": "DOUBLE"},
        ],
        [["2026-10-01", "01:02:03", "2026-10-01T12:00:00", "2026-10-01T12:00:00Z", "a", "1.50", "1", {"x": 1}, 1.5]],
    )
    assert str(frame["day"].iloc[0]) == "2026-10-01"  # type: ignore[index]
    assert frame["kind"].iloc[0] == "a"  # type: ignore[index]
    assert frame["geom"].iloc[0] == {"x": 1}  # type: ignore[index]
    assert frame["score"].iloc[0] == 1.5  # type: ignore[index]


def test_nested_values_stay_objects_and_empty_columns_stay_empty() -> None:
    """LIST and STRUCT are not flattened, and a header with no rows is empty."""
    nested = _frame([{"name": "tags", "type": "LIST<VARCHAR>"}], [[["a", "b"]]])
    assert nested["tags"].iloc[0] == ["a", "b"]  # type: ignore[index]
    empty = _frame([{"name": "n", "type": "BIGINT"}], [])
    blank = FetchQueryDeserializer()({"columns": [], "rows": []})
    assert blank.empty
    assert empty.empty  # type: ignore[attr-defined]
    assert list(empty.columns) == ["n"]  # type: ignore[attr-defined]


def test_payload_shape_and_bad_casts_fail() -> None:
    """A result must be a rectangle, and values must match the declared type."""
    deserializer = FetchQueryDeserializer()
    with pytest.raises(DeserializationError, match="JSON object"):
        deserializer(["nope"])
    with pytest.raises(DeserializationError, match="columns"):
        deserializer({"rows": []})
    with pytest.raises(DeserializationError, match="rows"):
        deserializer({"columns": []})
    with pytest.raises(DeserializationError, match="name or type"):
        deserializer({"columns": [{"name": "n"}], "rows": []})
    with pytest.raises(DeserializationError, match="repeats"):
        deserializer({"columns": [{"name": "n", "type": "BIGINT"}, {"name": "n", "type": "BIGINT"}], "rows": []})
    with pytest.raises(DeserializationError, match="match"):
        deserializer({"columns": [{"name": "n", "type": "BIGINT"}], "rows": [[1, 2]]})
    with pytest.raises(DeserializationError, match="cannot be cast"):
        deserializer({"columns": [{"name": "n", "type": "BIGINT"}], "rows": [["nope"]], "row_count": 1})


def test_bytes_body_is_accepted() -> None:
    """The deserializer accepts the raw response body as well as a parsed object."""
    frame = FetchQueryDeserializer()(b'{"columns":[{"name":"n","type":"BIGINT"}],"rows":[[7]],"row_count":1}')
    assert frame["n"].iloc[0] == 7


def test_next_page_cursor_is_the_following_offset() -> None:
    """Truncation says another page exists. The cursor is the next absolute offset."""
    deserializer = FetchQueryDeserializer()
    body = {"truncated": True, "row_count": 2}
    assert deserializer.get_next(body) is True
    assert deserializer.get_end_cursor(body, offset=10) == "12"
    assert deserializer.get_next({"truncated": False, "row_count": 2}) is False
    assert deserializer.get_end_cursor({"truncated": True, "row_count": 0}, offset=0) is None
