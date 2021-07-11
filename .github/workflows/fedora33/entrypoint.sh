#!/usr/bin/env bash
set -e
xgettext --version

# Leave source locally, otherwise some tests go mad (via get_module_dir)...
poetry install --no-root -E plugins

export PYTEST_ADDOPTS='-rxXs -m "not quality"'
sudo -u user echo "Running tests with $PYTEST_ADDOPTS"
sudo -u user poetry run python3 setup.py test
