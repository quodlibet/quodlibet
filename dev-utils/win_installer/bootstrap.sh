#!/usr/bin/env bash
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

set -e

function main {
    pacman --noconfirm -Suy

    pacman --noconfirm -S --needed \
        git \
        "${MINGW_PACKAGE_PREFIX}"-gettext \
        "${MINGW_PACKAGE_PREFIX}"-gdk-pixbuf2 \
        "${MINGW_PACKAGE_PREFIX}"-librsvg \
        "${MINGW_PACKAGE_PREFIX}"-gtk3 \
        "${MINGW_PACKAGE_PREFIX}"-libsoup3 \
        "${MINGW_PACKAGE_PREFIX}"-gstreamer \
        "${MINGW_PACKAGE_PREFIX}"-gst-plugins-base \
        "${MINGW_PACKAGE_PREFIX}"-gst-plugins-good \
        "${MINGW_PACKAGE_PREFIX}"-libsrtp \
        "${MINGW_PACKAGE_PREFIX}"-gst-plugins-bad \
        "${MINGW_PACKAGE_PREFIX}"-gst-libav \
        "${MINGW_PACKAGE_PREFIX}"-gst-plugins-ugly \
        "${MINGW_PACKAGE_PREFIX}"-cc

    pacman --noconfirm -S --needed \
        "${MINGW_PACKAGE_PREFIX}"-python \
        "${MINGW_PACKAGE_PREFIX}"-python-gobject \
        "${MINGW_PACKAGE_PREFIX}"-python-cairo \
        "${MINGW_PACKAGE_PREFIX}"-python-pip \
        "${MINGW_PACKAGE_PREFIX}"-python-pytest \
        "${MINGW_PACKAGE_PREFIX}"-python-certifi \
        "${MINGW_PACKAGE_PREFIX}"-python-coverage \
        "${MINGW_PACKAGE_PREFIX}"-python-mutagen

    pip install --break-system-packages --user -U feedparser musicbrainzngs
}

main
