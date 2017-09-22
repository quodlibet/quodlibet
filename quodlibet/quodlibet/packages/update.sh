#!/bin/bash

set -e

DIR="$( cd "$( dirname "$0" )" && pwd )"

rm -Rf "senf"
pip install --system --no-compile --no-deps --target="$DIR/tmp" "senf==1.3.1"
mv "$DIR/tmp/senf" "$DIR"
rm -R "$DIR/tmp"
