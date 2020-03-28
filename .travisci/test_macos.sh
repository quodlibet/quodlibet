#!/bin/bash

set -e

.circleci/retry wget -O ql.dmg https://github.com/quodlibet/quodlibet/releases/download/ci/QuodLibet-latest-v7.dmg
hdiutil attach -readonly -mountpoint _mount ql.dmg
cp -R _mount/QuodLibet.app "$TMPDIR/_app"
hdiutil detach _mount
RUN="$TMPDIR/_app/Contents/MacOS/run"
$RUN -m pip install flake8 pytest pytest-faulthandler "coverage[toml]"
$RUN -R -bb -m coverage run --branch setup.py test
$RUN  -R -bb -m coverage xml
bash <(curl -s https://codecov.io/bash)
