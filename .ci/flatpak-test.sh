#!/bin/bash

set -e

DIR="$( cd "$( dirname "$0" )" && pwd )"

if [[ $1 == "inflatpak" ]]; then
    python3 -m pip install --user pytest flake8
    python3 setup.py test
else
    xvfb-run -a flatpak run --user --command="bash" io.github.quodlibet.QuodLibet "${DIR}"/flatpak-test.sh inflatpak
fi
