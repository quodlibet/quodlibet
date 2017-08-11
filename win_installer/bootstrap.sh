#!/usr/bin/env bash
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

set -e

function install_python_packages {
    pacman --noconfirm -S --needed \
        mingw-w64-i686-python$1 \
        mingw-w64-i686-python$1-gobject \
        mingw-w64-i686-python$1-cairo \
        mingw-w64-i686-python$1-pip \
        mingw-w64-i686-python$1-pytest \
        mingw-w64-i686-python$1-certifi \

    pip$1 install feedparser musicbrainzngs mutagen pycodestyle pyflakes \
        coverage

    if [ "$1" = "2" ]; then
        pip$1 install --no-binary ":all:" futures faulthandler
    fi

}

function main {
    pacman --noconfirm -Suy

    pacman --noconfirm -S --needed \
        git mingw-w64-i686-gdk-pixbuf2 \
        mingw-w64-i686-librsvg \
        mingw-w64-i686-gtk3 \
        mingw-w64-i686-libsoup mingw-w64-i686-gstreamer \
        mingw-w64-i686-gst-plugins-base \
        mingw-w64-i686-gst-plugins-good mingw-w64-i686-libsrtp \
        mingw-w64-i686-gst-plugins-bad mingw-w64-i686-gst-libav \
        mingw-w64-i686-gst-plugins-ugly intltool \
        base-devel mingw-w64-i686-toolchain

    install_python_packages 2
    install_python_packages 3
}

main;
