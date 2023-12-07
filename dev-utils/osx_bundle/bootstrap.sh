#!/bin/bash

set -e

# shellcheck source-path=SCRIPTDIR
source env.sh

# to allow bootstrapping again, try to delete everything first
# shellcheck source-path=SCRIPTDIR
source clean.sh

# Cargo and Rust must be installed in the user's home directory.
# They cannot be run successfully from JHBuild's prefix or home
# directory.
rustup install 1.69.0

JHBUILD_REVISION="3.38.0"

mkdir -p "$HOME"
git clone https://github.com/GNOME/jhbuild.git "$QL_OSXBUNDLE_JHBUILD_DEST"
(cd "$QL_OSXBUNDLE_JHBUILD_DEST" && git checkout "$JHBUILD_REVISION" && ./autogen.sh && make -f Makefile.plain DISABLE_GETTEXT=1 install >/dev/null)
cp misc/gtk-osx-jhbuildrc "$HOME/.jhbuildrc"
cp misc/quodlibet-jhbuildrc-custom "$HOME/.jhbuildrc-custom"
git clone https://github.com/GNOME/gtk-mac-bundler.git "$QL_OSXBUNDLE_BUNDLER_DEST"
(cd "$QL_OSXBUNDLE_BUNDLER_DEST" && make install)
