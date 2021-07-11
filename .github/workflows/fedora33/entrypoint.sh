#!/usr/bin/env bash
set -e

# Leave source locally, otherwise some tests go mad (via get_module_dir)...
sudo -u user poetry install --no-root -E plugins

sudo -u user PYTEST_ADDOPTS='-rxXs -m "not quality"' poetry run python3 setup.py test
