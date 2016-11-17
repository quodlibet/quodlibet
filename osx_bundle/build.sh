#!/bin/bash

set -e

source env.sh

jhbuild build meta-bootstrap
jhbuild build python
jhbuild build meta-gtk-osx-bootstrap
jhbuild build quodlibet
