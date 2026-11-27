# ds-provider-aic-py-lib

![Python Versions](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue)
[![PyPI version](https://badge.fury.io/py/ds-provider-aic-py-lib.svg?kill_cache=1)](https://badge.fury.io/py/ds-provider-aic-py-lib)
[![Build Status](https://github.com/grasp-labs/ds-provider-aic-py-lib/actions/workflows/build.yaml/badge.svg)](https://github.com/grasp-labs/ds-provider-aic-py-lib/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/grasp-labs/ds-provider-aic-py-lib/graph/badge.svg?token=EO3YCNCZFS)](https://codecov.io/gh/grasp-labs/ds-provider-aic-py-lib)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Read-only AIC gold datasets and an identity linked service for the fetch API.

Sign in with OAuth2 client credentials or with a username and password.
``AICGoldDataset.read()`` requires SQL. Pagination stays inside that
call, and ``output`` is the full frame.
Gold mutation methods are not supported.

See [the provider guide](docs/source/provider.rst) for exposed and internal fields.

## Quick Start

### Quick Setup

```shell
# 1. Install dependencies
uv sync --all-extras --dev

# 2. Install pre-commit hooks
uv run pre-commit install

# 3. Verify setup
make test
```

## Development

### Available Commands

Use the Makefile for all development tasks:

```shell
# Show all available commands
make help

# Code Quality
make lint           # Check code quality with ruff
make format         # Format code with ruff
make type-check     # Run mypy type checking
make security-check # Run security checks with bandit

# Testing
make test          # Run tests
make test-cov      # Run tests with coverage (requires 95%)

# Build and Publish
make build         # Build package
make docs          # Build documentation
make publish-test  # Upload to TestPyPI
make publish       # Upload to PyPI
```

### Version Management

```shell
# Show current version
make version

# Tag and release
make tag           # Create git tag and push (triggers release)
```

> **⚠️ Warning**: The `make tag` command will create a git tag and
> push it to the remote repository, which may trigger automated
> releases. Ensure you have updated `pyproject.toml` with the new version
> and committed all changes before running this command.

### Pre-commit Hooks

```shell
uv run pre-commit install
uv run pre-commit run --all-files
```

### Building Documentation

```shell
# Build documentation
make docs

# View documentation (macOS)
open docs/build/html/index.html

# View documentation (Linux)
xdg-open docs/build/html/index.html
```

### Testing

```shell
# Run basic tests
make test

# Run tests with coverage (requires 95% coverage)
make test-cov

# Run one test module
uv run pytest tests/dataset/test_gold.py -v
```

## Project Structure

```text
.
├── .config/                         # Tooling config
├── .github/                         # CI workflows
├── docs/source/                     # Sphinx pages
├── examples/                        # Live scripts, credentials from .env
├── src/ds_provider_aic_py_lib/
│   ├── dataset/                     # Read-only gold dataset
│   ├── linked_service/              # AIC identity session
│   ├── serde/                       # Fetch query deserializer
│   ├── enums.py
│   └── resource.yaml                # Provider registration
├── tests/
├── CONTRIBUTING.md
├── Makefile
├── PyPI.md                          # Package readme published to PyPI
├── README.md
└── pyproject.toml
```

## Features

- **Identity linked service**: Client credentials and username/password
  through the HTTP protocol, with AIC defaults
- **Read-only gold dataset**: Required SQL, with pagination inside ``read()``
- **Fetch deserializer**: Query pages become frames with DuckDB dtypes
- **Modern Python Tooling**: Uses `uv` for fast dependency management
- **Type Safety**: Strict mypy configuration with full type hints
- **Code Quality**: Ruff for linting and formatting
- **Testing**: Pytest with 95% coverage requirement
- **Documentation**: Sphinx with autoapi for automatic API docs
- **CI/CD**: GitHub Actions for testing, building, and publishing
- **Pre-commit Hooks**: Automated code quality checks

## Examples

Copy `.env.example` to `.env` and fill in credentials.

```shell
uv run --extra dev python examples/01_linked_service_client_credentials.py
uv run --extra dev python examples/02_linked_service_password.py
uv run --extra dev python examples/03_dataset_gold_read.py
uv run --extra dev python examples/04_dataset_gold_list.py
uv run --extra dev python examples/05_dataset_gold_parallel_read.py
```

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Make (for development commands)

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [PyPI.md](PyPI.md) - Package readme published to PyPI
- [README.md](README.md) - This file

## License

This package is licensed under the Apache License 2.0.
See [LICENSE-APACHE](LICENSE-APACHE) for details.
