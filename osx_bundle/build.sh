#!/bin/sh

source env.sh

jhbuild build autoconf --nodeps
jhbuild bootstrap
jhbuild build python
jhbuild build meta-gtk-osx-bootstrap
jhbuild build quodlibet