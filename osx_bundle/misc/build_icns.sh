#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"
APPS="$DIR"/../../quodlibet/quodlibet/images/hicolor/scalable/apps

python svg2icns.py "$APPS"/quodlibet.svg "$DIR"/bundle/quodlibet.icns
python svg2icns.py "$APPS"/exfalso.svg "$DIR"/bundle/exfalso.icns
