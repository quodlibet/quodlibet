#!/usr/bin/env bash
set -e
# Fix for hanging flake8 test
# https://github.com/quodlibet/quodlibet/issues/3539#issuecomment-767389459
poetry config virtualenvs.in-project true

poetry install -E plugins
export PYTEST_ADDOPTS=-rxXs
sudo -u user poetry run setup.py test
