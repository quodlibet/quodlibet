#!/bin/bash

set -e

DIR="$( cd "$( dirname "$0" )" && pwd )"

if [[ $1 == "inflatpak" ]]; then
    tmp="$(mktemp -d)"
    python3 -m venv --system-site-packages "$tmp"
    "$tmp"/bin/python3 -m pip install pytest flake8==5.0.4 flaky
    "$tmp"/bin/python3 setup.py test
else
    xvfb-run -a flatpak run --devel --user --command="bash" io.github.quodlibet.QuodLibet "${DIR}"/flatpak-test.sh inflatpak
fi
