#!/usr/bin/env bash
set -e

# Fix for hanging flake8 test
# https://github.com/quodlibet/quodlibet/issues/3539#issuecomment-767389459
poetry config virtualenvs.in-project true

poetry install -E plugins
PYTEST_ADDOPTS=-rxXs poetry run python3 setup.py test
