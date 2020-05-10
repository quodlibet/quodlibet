#!/bin/bash

set -e

export MSYS2_FC_CACHE_SKIP=1

pacman --noconfirm -Suy

pacman --noconfirm -S --needed \
    mingw-w64-$MSYS2_ARCH-libxml2 \
    mingw-w64-$MSYS2_ARCH-brotli

pacman --noconfirm -S --needed \
    git \
    mingw-w64-$MSYS2_ARCH-gettext \
    mingw-w64-$MSYS2_ARCH-gdk-pixbuf2 \
    mingw-w64-$MSYS2_ARCH-librsvg \
    mingw-w64-$MSYS2_ARCH-gtk3 \
    mingw-w64-$MSYS2_ARCH-libsoup \
    mingw-w64-$MSYS2_ARCH-gstreamer \
    mingw-w64-$MSYS2_ARCH-gst-plugins-base \
    mingw-w64-$MSYS2_ARCH-gst-plugins-good \
    mingw-w64-$MSYS2_ARCH-gst-plugins-bad \
    mingw-w64-$MSYS2_ARCH-gst-libav \
    mingw-w64-$MSYS2_ARCH-gst-plugins-ugly \
    mingw-w64-$MSYS2_ARCH-python3 \
    mingw-w64-$MSYS2_ARCH-python3-gobject \
    mingw-w64-$MSYS2_ARCH-python3-cairo \
    mingw-w64-$MSYS2_ARCH-python3-pip \
    mingw-w64-$MSYS2_ARCH-python3-pytest \
    mingw-w64-$MSYS2_ARCH-python3-certifi \
    mingw-w64-$MSYS2_ARCH-python3-coverage \
    mingw-w64-$MSYS2_ARCH-python3-flake8 \
    mingw-w64-$MSYS2_ARCH-python-entrypoints \
    mingw-w64-$MSYS2_ARCH-python3-toml

pip3 install feedparser musicbrainzngs mutagen
