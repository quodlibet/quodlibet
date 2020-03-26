#!/bin/bash
# run the test suite in our flatpak package

set -e

if [[ $1 == "inflatpak" ]]; then
    cd quodlibet
    python3 -m venv --system-site-packages /tmp/_flatpak_venv
    source /tmp/_flatpak_venv/bin/activate
    python3 -m pip install pytest pyflakes pycodestyle
    python3 setup.py test
else
    flatpak run --devel --command="bash" \
        io.github.quodlibet.QuodLibet test_flatpak.sh inflatpak
fi
