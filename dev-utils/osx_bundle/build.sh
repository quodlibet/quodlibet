#!/bin/bash

set -e

# shellcheck source-path=SCRIPTDIR
source env.sh

cargo -V || (echo "Requires rust"; exit 1)

# install ninja
# shellcheck disable=SC2016
BIN=$(jhbuild run bash -c 'echo $PREFIX/bin')
curl -L -o ninja.zip "https://github.com/ninja-build/ninja/releases/download/v1.8.2/ninja-mac.zip"
unzip -o ninja.zip -d "$BIN"
rm ninja.zip

jhbuild build meta-bootstrap
jhbuild build quodlibet
