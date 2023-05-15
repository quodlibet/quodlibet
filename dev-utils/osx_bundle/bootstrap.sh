#!/bin/bash

set -e

source env.sh

# to allow bootstrapping again, try to delete everything first
rm -Rf "$QL_OSXBUNDLE_JHBUILD_DEST"
rm -Rf "$QL_OSXBUNDLE_BUNDLER_DEST"
rm -Rf "$HOME/.local"
rm -f "$HOME/.jhbuildrc"
rm -f "$HOME/.jhbuildrc-custom"

rustup install 1.69.0

JHBUILD_REVISION="624bcf68591aaa17d9f6119c8b9672b92ac6120c"

mkdir -p "$HOME"
git clone https://gitlab.gnome.org/GNOME/jhbuild.git "$QL_OSXBUNDLE_JHBUILD_DEST"
(cd "$QL_OSXBUNDLE_JHBUILD_DEST" && git checkout "$JHBUILD_REVISION" && ./autogen.sh && make -f Makefile.plain DISABLE_GETTEXT=1 install >/dev/null)
cp misc/gtk-osx-jhbuildrc "$HOME/.jhbuildrc"
cp misc/quodlibet-jhbuildrc-custom "$HOME/.jhbuildrc-custom"
git clone https://gitlab.gnome.org/GNOME/gtk-mac-bundler.git "$QL_OSXBUNDLE_BUNDLER_DEST"
(cd "$QL_OSXBUNDLE_BUNDLER_DEST" && make install)
