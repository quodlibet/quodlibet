#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"

rm -Rf "raven"
pip install --system --no-compile --no-deps --target="$DIR/tmp" "raven==6.3.0"
mv "$DIR/tmp/raven" "$DIR"
rm -R "$DIR/tmp"

rm -R "$DIR/raven/contrib/"
rm -R "$DIR/raven/data/"
