#!/bin/bash
# run the test suite in our flatpak package

set -e

if [[ $1 == "inflatpak" ]]; then
    cd ..
    python3 -m venv --system-site-packages /tmp/_flatpak_venv
    # shellcheck disable=SC1091
    source /tmp/_flatpak_venv/bin/activate
    python3 -m pip install pytest "ruff==0.1.6"
    python3 setup.py test
else
    flatpak run --env=LC_ALL=C.utf8 --devel --command="bash" \
        io.github.quodlibet.QuodLibet test_flatpak.sh inflatpak
fi
