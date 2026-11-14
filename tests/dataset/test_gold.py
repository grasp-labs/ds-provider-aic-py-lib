"""
**File:** ``test_gold.py``
**Region:** ``tests/dataset/test_gold``

Unit tests for the read-only AIC gold dataset.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from ds_protocol_http_py_lib.enums import AuthType
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ListError, ReadError
from ds_resource_plugin_py_lib.common.resource.errors import NotSupportedError
from ds_resource_plugin_py_lib.common.resource.linked_service.errors import ConnectionError

from ds_provider_aic_py_lib.dataset.gold import AICGoldDataset, AICGoldDatasetSettings, GoldListSettings, GoldReadSettings
from ds_provider_aic_py_lib.enums import HistoryMode, Layer, PublishMode, ResourceType
from ds_provider_aic_py_lib.linked_service.identity import (
    AICIdentityLinkedService,
    AICIdentityLinkedServiceSettings,
    AICIdentityOAuth2AuthSettings,
)

DATASET_ID = UUID("5003105c-8a84-5f77-ab74-5e57003112b8")


def _service() -> AICIdentityLinkedService:
    service = AICIdentityLinkedService(
        id=UUID("3c0ff9f2-b261-5cb2-b46c-1e5d9672a754"),
        name="aic-identity",
        version="v1.0.0",
        settings=AICIdentityLinkedServiceSettings(
            auth_type=AuthType.OAUTH2,
            oauth2=AICIdentityOAuth2AuthSettings(client_id="client", client_secret="secret"),
        ),
    )
    service._session = MagicMock()
    return service


def _response(payload: dict[str, object]) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.text = json.dumps(payload)
    return response


def _page(rows: list[list[object]], *, truncated: bool) -> dict[str, object]:
    return {
        "columns": [{"name": "n", "type": "BIGINT"}],
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "elapsed_ms": 1,
    }


def _dataset(**overrides: object) -> AICGoldDataset:
    read = overrides.pop("read", GoldReadSettings(sql='SELECT n FROM gold."5003105c-8a84-5f77-ab74-5e57003112b8"'))
    listing = overrides.pop("list", GoldListSettings())
    settings = AICGoldDatasetSettings(
        publish_mode=PublishMode.UPSERT,
        primary_key_fields=["employee_id"],
        ordering_field="updated_at",
        history_mode=HistoryMode.SCD2,
        partition_keys=["code"],
        read=read,  # type: ignore[arg-type]
        list=listing,  # type: ignore[arg-type]
    )
    return AICGoldDataset(
        id=DATASET_ID,
        name="employees",
        version="v1.0.0",
        linked_service=_service(),
        settings=settings,
    )


def test_read_qualifies_gold_with_the_dataset_id() -> None:
    """A bare gold table is this dataset. Repeating its own id, and string literals, stay legal."""
    dataset = _dataset(
        read=GoldReadSettings(
            sql=(
                "SELECT * FROM gold "
                f'JOIN gold."{DATASET_ID}" other ON other.id = gold.id '
                "WHERE note = 'gold.\"11111111-1111-1111-1111-111111111111\"'"
            ),
        ),
    )
    dataset.linked_service.connection.post.return_value = _response(_page([[1]], truncated=False))

    dataset.read()

    posted = dataset.linked_service.connection.post.call_args.kwargs["json"]["sql"]
    assert posted == (
        f'SELECT * FROM gold."{DATASET_ID}" '
        f'JOIN gold."{DATASET_ID}" other ON other.id = gold.id '
        "WHERE note = 'gold.\"11111111-1111-1111-1111-111111111111\"'"
    )


@pytest.mark.parametrize(
    "sql",
    [
        'SELECT * FROM gold."11111111-1111-1111-1111-111111111111"',
        'SELECT * FROM silver."1db82d2e-9316-54ae-8fe9-52fc2ea66301/342a019b-21b7-4659-92ce-c0c7740081ff"',
        'SELECT * FROM bronze."1db82d2e-9316-54ae-8fe9-52fc2ea66301/342a019b-21b7-4659-92ce-c0c7740081ff"',
        'SELECT * FROM gold JOIN gold."11111111-1111-1111-1111-111111111111" other ON true',
    ],
)
def test_read_rejects_another_dataset(sql: str) -> None:
    """This dataset cannot read any other gold, silver, or bronze dataset."""
    dataset = _dataset(read=GoldReadSettings(sql=sql))

    with pytest.raises(ReadError, match="another dataset"):
        dataset.read()

    dataset.linked_service.connection.post.assert_not_called()


def test_read_requires_sql() -> None:
    """read() does not invent a statement."""
    dataset = _dataset(read=None)
    with pytest.raises(ReadError, match="SQL is required"):
        dataset.read()


def test_read_yields_one_page_when_fetch_is_complete() -> None:
    """A complete result is a single frame and clears pagination state."""
    dataset = _dataset()
    dataset.linked_service.connection.post.return_value = _response(_page([[1], [2]], truncated=False))

    dataset.read()

    assert dataset.output["n"].tolist() == [1, 2]
    posted = dataset.linked_service.connection.post.call_args.kwargs
    assert posted["json"] == {"sql": dataset.settings.read.sql}
    assert "pagination" not in dataset.checkpoint
    assert dataset.operation.success is True


def test_read_follows_truncated_pages_inside_the_call() -> None:
    """One read walks every truncated page and returns the whole frame."""
    dataset = _dataset()
    dataset.checkpoint = {"pagination": {"offset": 2}}
    dataset.linked_service.connection.post.side_effect = [
        _response(_page([[3]], truncated=True)),
        _response(_page([[4]], truncated=False)),
    ]

    dataset.read()

    assert dataset.output["n"].tolist() == [3, 4]
    statements = [call.kwargs["json"]["sql"] for call in dataset.linked_service.connection.post.call_args_list]
    assert statements[0].endswith("OFFSET 2")
    assert statements[1].endswith("OFFSET 3")
    assert "pagination" not in dataset.checkpoint


def test_read_keeps_partial_output_when_a_later_page_fails() -> None:
    """A failed later page leaves the rows already fetched and the next offset."""
    dataset = _dataset()
    dataset.linked_service.connection.post.side_effect = [
        _response(_page([[3]], truncated=True)),
        ConnectionError(message="fetch down"),
    ]

    with pytest.raises(ReadError, match="fetch down"):
        dataset.read()

    assert dataset.output["n"].tolist() == [3]
    assert dataset.checkpoint["pagination"] == {"offset": 1}
    assert dataset.operation.success is False


def test_read_stops_when_a_truncated_page_has_no_rows() -> None:
    """An empty truncated page does not request another offset."""
    dataset = _dataset()
    dataset.linked_service.connection.post.return_value = _response(_page([], truncated=True))

    dataset.read()

    assert dataset.output.empty
    dataset.linked_service.connection.post.assert_called_once()


def test_read_wraps_a_bad_later_page_and_keeps_earlier_rows() -> None:
    """A page that cannot be deserialized is still a ReadError after partial output."""
    dataset = _dataset()
    dataset.linked_service.connection.post.side_effect = [
        _response(_page([[1]], truncated=True)),
        _response({"columns": [{"name": "n", "type": "BIGINT"}], "rows": "nope", "truncated": False, "row_count": 0}),
    ]

    with pytest.raises(ReadError, match="rows"):
        dataset.read()

    assert dataset.output["n"].tolist() == [1]
    assert dataset.checkpoint["pagination"] == {"offset": 1}


def test_read_wraps_transport_errors() -> None:
    """A failed first page is a ReadError on the read operation."""
    dataset = _dataset()
    dataset.linked_service.connection.post.side_effect = ConnectionError(message="fetch down")

    with pytest.raises(ReadError, match="fetch down"):
        dataset.read()
    assert dataset.operation.success is False


def test_read_rejects_a_non_object_body() -> None:
    """Fetch must return a JSON object."""
    dataset = _dataset()
    response = MagicMock()
    response.json.return_value = []
    dataset.linked_service.connection.post.return_value = response

    with pytest.raises(ReadError, match="not an object"):
        dataset.read()


def test_fresh_read_sends_cache_control() -> None:
    """fresh asks fetch to skip its cache."""
    dataset = _dataset(read=GoldReadSettings(sql="SELECT 1", fresh=True))
    dataset.linked_service.connection.post.return_value = _response(_page([[1]], truncated=False))

    dataset.read()

    headers = dataset.linked_service.connection.post.call_args.kwargs["headers"]
    assert headers["Cache-Control"] == "no-cache"


def test_list_pages_until_has_next_is_false() -> None:
    """list() follows the dataset catalog and deserializes each page."""
    dataset = _dataset(
        list=GoldListSettings(names=["gold.employees"], layers=[Layer.GOLD], limit=2, fresh=True),
    )
    dataset.linked_service.connection.get.side_effect = [
        _response({"data": [{"name": "gold.a"}], "page": {"has_next": True}}),
        _response({"data": [{"name": "gold.b"}], "page": {"has_next": False}}),
    ]

    dataset.list()

    assert dataset.output["name"].tolist() == ["gold.a", "gold.b"]
    first = dataset.linked_service.connection.get.call_args_list[0].kwargs
    assert first["params"] == [("limit", 2), ("offset", 0), ("name", "gold.employees"), ("layer", "gold")]
    assert first["headers"]["Cache-Control"] == "no-cache"
    second_offset = dataset.linked_service.connection.get.call_args_list[1].kwargs["params"][1]
    assert second_offset == ("offset", 1)


def test_list_rejects_a_bad_page_and_a_transport_error() -> None:
    """A catalog response that is not a page is a ListError."""
    dataset = _dataset()
    dataset.linked_service.connection.get.return_value = _response({"data": []})
    with pytest.raises(ListError, match="page"):
        dataset.list()

    dataset.linked_service.connection.get.side_effect = ConnectionError(message="fetch down")
    with pytest.raises(ListError, match="fetch down"):
        dataset.list()


def test_mutations_are_not_supported() -> None:
    """Gold is not owned by this provider."""
    dataset = _dataset()
    for method in ("create", "update", "upsert", "delete", "purge", "rename"):
        with pytest.raises(NotSupportedError):
            getattr(dataset, method)()


def test_close_closes_the_linked_service() -> None:
    """The dataset releases the identity session."""
    dataset = _dataset()
    dataset.linked_service._http.close = MagicMock()
    dataset.close()
    dataset.linked_service._http.close.assert_called_once()


def test_type_and_checkpoint_support() -> None:
    """The dataset type is gold and reads can resume from a pagination offset."""
    dataset = _dataset()
    assert dataset.type == ResourceType.DATASET_GOLD
    assert dataset.supports_checkpoint is True
    assert dataset.serializer is None
