#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"

rm -f "contextlib2.py"
pip install --no-compile --no-deps --target="$DIR/tmp" "contextlib2==0.5.5"
mv "$DIR/tmp/contextlib2.py" "$DIR"
rm -R "$DIR/tmp"

rm -Rf "raven"
pip install --no-compile --no-deps --target="$DIR/tmp" "git+https://github.com/getsentry/raven-python.git@005d7fb0238a598529f85d11ddf272d2214408d8"
mv "$DIR/tmp/raven" "$DIR"
rm -R "$DIR/tmp"

rm -R "$DIR/raven/contrib/"
rm -R "$DIR/raven/data/"
