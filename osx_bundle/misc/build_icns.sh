#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"
APPS="$DIR"/../../quodlibet/quodlibet/images/hicolor/scalable/apps

python3 svg2icns.py "$APPS"/io.github.quodlibet.QuodLibet.svg "$DIR"/bundle/quodlibet.icns
python3 svg2icns.py "$APPS"/io.github.quodlibet.ExFalso.svg "$DIR"/bundle/exfalso.icns
