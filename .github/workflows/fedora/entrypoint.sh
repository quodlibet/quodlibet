#!/usr/bin/env bash
set -e

# Leave source locally, otherwise some tests go mad (via get_module_dir)...
sudo -u user pipx run poetry==2.1.2 install -E plugins

sudo -u user PYTEST_ADDOPTS='-rxXs -m "not quality"' pipx run poetry==2.1.2 run python3 setup.py test
