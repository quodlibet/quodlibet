#!/usr/bin/env bash
set -e
sudo -u user poetry install -E plugins
export PYTEST_ADDOPTS=-rxXs
sudo -u user poetry run setup.py test
