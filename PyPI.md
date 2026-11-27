# ds-provider-aic-py-lib

DS package for ds-provider-aic-py-lib

## Installation

Install the package using pip:

```bash
pip install ds-provider-aic-py-lib
```

Or using uv (recommended):

```bash
uv pip install ds-provider-aic-py-lib
```

## Quick Start

```python
from uuid import uuid4

from ds_protocol_http_py_lib.enums import AuthType

from ds_provider_aic_py_lib.dataset.gold import (
    AICGoldDataset,
    AICGoldDatasetSettings,
    GoldReadSettings,
)
from ds_provider_aic_py_lib.enums import HistoryMode, PublishMode
from ds_provider_aic_py_lib.linked_service.identity import (
    AICIdentityLinkedService,
    AICIdentityLinkedServiceSettings,
    AICIdentityOAuth2AuthSettings,
)

linked_service = AICIdentityLinkedService(
    id=uuid4(),
    name="aic-identity",
    version="v1.0.0",
    settings=AICIdentityLinkedServiceSettings(
        auth_type=AuthType.OAUTH2,
        oauth2=AICIdentityOAuth2AuthSettings(
            client_id="client",
            client_secret="secret",
        ),
    ),
)
dataset = AICGoldDataset(
    id=uuid4(),
    name="employees",
    version="v1.0.0",
    linked_service=linked_service,
    settings=AICGoldDatasetSettings(
        publish_mode=PublishMode.UPSERT,
        primary_key_fields=["employee_id"],
        history_mode=HistoryMode.SCD2,
        partition_keys=[],
        read=GoldReadSettings(sql="SELECT count(*) AS n FROM gold"),
    ),
)
linked_service.connect()
dataset.read()
dataset.output
```

## Features

- Identity linked service with OAuth2 client credentials and
  username/password login
- Read-only gold dataset over the fetch API
- SQL is required. Name this dataset `gold`. That name is rewritten to
  this dataset id. A quoted reference to another dataset is rejected
  here. Fetch grants decide any other name
- A result that spans more than one page needs `ORDER BY` so later
  pages keep a stable row order
- `read()` deserializes each query page with `FetchQueryDeserializer`

## Usage

Gold mutation is not supported. `create`, `update`, `upsert`, `delete`,
`purge`, and `rename` raise `NotSupportedError`.

The repository `examples/` scripts read credentials from `.env`.
They are not installed with the package.

## Requirements

- Python 3.11 or higher
- `ds-resource-plugin-py-lib`
- `ds-protocol-http-py-lib`
- `ds-common-serde-py-lib`
- `pandas`
- `pyarrow`

## Optional Dependencies

- `dev`: lint, types, tests, docs, and `python-dotenv` for the examples
- `test`: pytest
- `docs`: Sphinx

## Documentation

Full documentation is available at:

- [GitHub Repository](https://github.com/grasp-labs/ds-provider-aic-py-lib)
- [Documentation Site](https://grasp-labs.github.io/ds-provider-aic-py-lib/)

## Development

To contribute or set up a development environment:

```bash
# Clone the repository
git clone https://github.com/grasp-labs/ds-provider-aic-py-lib.git
cd ds-provider-aic-py-lib

# Install development dependencies
uv sync --all-extras --dev

# Run tests
make test
```

See the [README](https://github.com/grasp-labs/ds-provider-aic-py-lib#readme)
for more information.

## License

This package is licensed under the Apache License 2.0.
See the [LICENSE-APACHE](https://github.com/grasp-labs/ds-provider-aic-py-lib/blob/main/LICENSE-APACHE)
file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/grasp-labs/ds-provider-aic-py-lib/issues)
- **Releases**: [GitHub Releases](https://github.com/grasp-labs/ds-provider-aic-py-lib/releases)
