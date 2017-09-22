#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"

rm -f "contextlib2.py"
pip install --system --no-compile --no-deps --target="$DIR/tmp" "contextlib2==0.5.5"
mv "$DIR/tmp/contextlib2.py" "$DIR"
rm -R "$DIR/tmp"

rm -Rf "raven"
pip install --system --no-compile --no-deps --target="$DIR/tmp" "raven==6.1.0"
mv "$DIR/tmp/raven" "$DIR"
rm -R "$DIR/tmp"

rm -R "$DIR/raven/contrib/"
rm -R "$DIR/raven/data/"
