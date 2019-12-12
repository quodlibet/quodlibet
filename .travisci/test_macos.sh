#!/bin/bash

set -e

.circleci/retry wget -O ql.dmg https://github.com/quodlibet/quodlibet/releases/download/ci/QuodLibet-latest-v6.dmg
hdiutil attach -readonly -mountpoint _mount ql.dmg
cd quodlibet
../_mount/QuodLibet.app/Contents/MacOS/run -R -bb -m coverage run --branch setup.py test
../_mount/QuodLibet.app/Contents/MacOS/run -R -bb -m coverage xml
bash <(curl -s https://codecov.io/bash)
