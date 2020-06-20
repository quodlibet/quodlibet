#!/bin/bash

set -e

export PYTEST_ADDOPTS="-v --junitxml=junit/test-results.xml"

MSYSTEM= python3 -R -bb setup.py test
