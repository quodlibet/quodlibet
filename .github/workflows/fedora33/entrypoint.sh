#!/usr/bin/env bash

# Fix for hanging flake8 test
# https://github.com/quodlibet/quodlibet/issues/3539#issuecomment-767389459
poetry config virtualenvs.in-project true

poetry install -E plugins
sudo -u user poetry run python3 setup.py test
