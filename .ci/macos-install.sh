#!/bin/bash

set -e

.ci/retry wget -O ql.dmg https://github.com/quodlibet/quodlibet/releases/download/ci/QuodLibet-latest-v11.dmg
hdiutil attach -noverify -readonly -mountpoint _mount ql.dmg
cp -R _mount/QuodLibet.app "$TMPDIR/_app"
hdiutil detach -force _mount
RUN="$TMPDIR/_app/Contents/MacOS/run"
$RUN -m pip install "ruff==0.7.3" "pytest==7.4.4" pytest-faulthandler flaky "coverage[toml]"
