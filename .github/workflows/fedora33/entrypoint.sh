#!/usr/bin/env bash
set -e
# Fix for hanging flake8 test
# https://github.com/quodlibet/quodlibet/issues/3539#issuecomment-767389459
poetry config virtualenvs.in-project true

# Leave source locally, otherwise some tests go mad (via get_module_dir)...
poetry install -E plugins --no-root

export PYTEST_ADDOPTS='-rxXs -m "not quality"'
xgettext --version; xgettext --help
sudo -u user echo "Running tests with $PYTEST_ADDOPTS"
sudo -u user poetry run python3 setup.py test
