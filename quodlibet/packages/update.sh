#!/bin/bash

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

rm -Rf "senf"
pip3 install --system --no-compile --no-deps --target="$DIR/tmp" "senf==1.5.0"
mv "$DIR/tmp/senf" "$DIR"
rm -R "$DIR/tmp"

rm "$DIR/senf/py.typed"
