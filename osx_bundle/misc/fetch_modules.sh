#!/bin/bash

set -e

source ../env.sh

git clone git://git.gnome.org/gtk-osx _gtk-osx
cp -R _gtk-osx/modulesets-stable/. ../modulesets/
cp _gtk-osx/jhbuildrc-gtk-osx gtk-osx-jhbuildrc
rm -Rf _gtk-osx
