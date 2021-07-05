#!/usr/bin/env bash
set -e
poetry install -E plugins
export PYTEST_ADDOPTS=-rxXs
sudo -u user poetry run setup.py test
