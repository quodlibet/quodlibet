#!/bin/bash

set -e

source env.sh

# to allow bootstrapping again, try to delete everything first
rm -Rf "$QL_OSXBUNDLE_JHBUILD_DEST"
rm -Rf "$QL_OSXBUNDLE_BUNDLER_DEST"
rm -Rf "$HOME/.local"
rm -f "$HOME/.jhbuildrc"
rm -f "$HOME/.jhbuildrc-custom"

JHBUILD_REVISION="fe1552ad15999f023b01bc009dabb1b1956cd9ac"

mkdir -p "$HOME"
git clone git://git.gnome.org/jhbuild "$QL_OSXBUNDLE_JHBUILD_DEST"
(cd "$QL_OSXBUNDLE_JHBUILD_DEST" && git checkout "$JHBUILD_REVISION" && ./autogen.sh && make -f Makefile.plain DISABLE_GETTEXT=1 install >/dev/null)
cp misc/gtk-osx-jhbuildrc "$HOME/.jhbuildrc"
cp misc/quodlibet-jhbuildrc-custom "$HOME/.jhbuildrc-custom"
git clone git://git.gnome.org/gtk-mac-bundler "$QL_OSXBUNDLE_BUNDLER_DEST"
(cd "$QL_OSXBUNDLE_BUNDLER_DEST" && make install)
