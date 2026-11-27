"""
**File:** ``sql.py``
**Region:** ``ds_provider_aic_py_lib/dataset/utils/sql``

Scope a gold statement to one dataset and move a later page with ``OFFSET``.
"""

import re

from ds_resource_plugin_py_lib.common.resource.dataset.errors import ReadError

_GOLD_TABLE = re.compile(r"""(?P<literal>'(?:''|[^'])*')|(?P<keyword>\b(?:FROM|JOIN)\s+)gold\b(?!\s*\.)""", re.IGNORECASE)


_OTHER_DATASET = re.compile(
    r"""(?P<literal>'(?:''|[^'])*')|(?P<schema>gold|silver|bronze)\s*\.\s*"(?P<name>(?:[^"]|"")*)\"""",
    re.IGNORECASE,
)


def qualify(sql: str, dataset_id: object) -> str:
    """Rewrite ``gold`` to this dataset. A quoted reference to another dataset is rejected."""
    table = "".join(('gold."', str(dataset_id), '"'))

    def replace(match: re.Match[str]) -> str:
        literal = match.group("literal")
        if literal is not None:
            return literal
        return f"{match.group('keyword')}{table}"

    scoped = _GOLD_TABLE.sub(replace, sql)
    own = str(dataset_id).lower()
    for match in _OTHER_DATASET.finditer(scoped):
        if match.group("schema") is None:
            continue
        schema = match.group("schema").lower()
        name = match.group("name").replace('""', '"').lower()
        if schema != "gold" or name != own:
            raise ReadError(message="This dataset cannot read another dataset.")
    return scoped


def statement(sql: str, offset: int) -> str:
    """Return ``sql`` unchanged, or the same statement moved by ``offset`` rows.

    The wrapper keeps row order only when ``sql`` has ``ORDER BY``. The newline
    before the closing parenthesis keeps a trailing ``--`` comment from swallowing it.
    """
    if offset <= 0:
        return sql
    inner = sql.strip().rstrip(";")
    return "".join(("SELECT * FROM (", inner, "\n) AS _aic_page OFFSET ", str(offset)))
