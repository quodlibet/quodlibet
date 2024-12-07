#!/bin/bash

set -e

# shellcheck source-path=SCRIPTDIR
source env.sh

cargo -V || (
    echo "Requires rust"
    exit 1
)

jhbuild build meta-bootstrap
jhbuild build quodlibet
