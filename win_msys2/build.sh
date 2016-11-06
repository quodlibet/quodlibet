#!/usr/bin/env bash
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

set -e
DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "${DIR}"


BUILD_ROOT="${DIR}/_build_root"
ARCH="i686"
PYTHON_VERSION="2"

PYTHON_ID="python${PYTHON_VERSION}"
if [ "${ARCH}" = "x86_64" ]; then
    MINGW="mingw64"
else
    MINGW="mingw32"
fi
REPO_CLONE="${BUILD_ROOT}"/quodlibet


build_pacman() {
    pacman --root "${BUILD_ROOT}" "$@"
}

build_pip() {
    "${BUILD_ROOT}"/"${MINGW}"/bin/"${PYTHON_ID}".exe -m pip "$@"
}

build_python() {
    "${BUILD_ROOT}"/"${MINGW}"/bin/"${PYTHON_ID}".exe "$@"
}

create_root() {
    mkdir -p "${BUILD_ROOT}"

    mkdir -p "${BUILD_ROOT}"/var/lib/pacman
    mkdir -p "${BUILD_ROOT}"/var/log
    mkdir -p "${BUILD_ROOT}"/tmp

    build_pacman -Syu
    build_pacman --noconfirm -S base
}

install_deps() {

    build_pacman --noconfirm -S git mingw-w64-"${ARCH}"-gdk-pixbuf2 \
        mingw-w64-"${ARCH}"-librsvg \
        mingw-w64-"${ARCH}"-gtk3 mingw-w64-"${ARCH}"-"${PYTHON_ID}" \
        mingw-w64-"${ARCH}"-"${PYTHON_ID}"-gobject \
        mingw-w64-"${ARCH}"-"${PYTHON_ID}"-pip \
        mingw-w64-"${ARCH}"-libsoup mingw-w64-"${ARCH}"-gstreamer \
        mingw-w64-"${ARCH}"-gst-plugins-base \
        mingw-w64-"${ARCH}"-gst-plugins-good mingw-w64-"${ARCH}"-libsrtp \
        mingw-w64-"${ARCH}"-gst-plugins-bad mingw-w64-"${ARCH}"-gst-libav \
        mingw-w64-"${ARCH}"-gst-plugins-ugly

    # FIXME
    build_pacman --noconfirm -U "${DIR}"/*.pkg.tar.xz

    build_pip install mutagen futures feedparser certifi pytest pep8 \
        pyflakes musicbrainzngs

    build_pacman --noconfirm -Rdd mingw-w64-"${ARCH}"-shared-mime-info \
        mingw-w64-"${ARCH}"-"${PYTHON_ID}"-pip mingw-w64-"${ARCH}"-ncurses \
        mingw-w64-"${ARCH}"-tk mingw-w64-"${ARCH}"-tcl \
        mingw-w64-"${ARCH}"-opencv mingw-w64-"${ARCH}"-daala-git \
        mingw-w64-"${ARCH}"-SDL2 mingw-w64-"${ARCH}"-libdvdcss \
        mingw-w64-"${ARCH}"-libdvdnav mingw-w64-"${ARCH}"-libdvdread \
        mingw-w64-"${ARCH}"-openexr mingw-w64-"${ARCH}"-openal \
        mingw-w64-"${ARCH}"-openh264 mingw-w64-"${ARCH}"-gnome-common \
        mingw-w64-"${ARCH}"-clutter  mingw-w64-"${ARCH}"-gsl \
        mingw-w64-"${ARCH}"-libvpx mingw-w64-"${ARCH}"-libcaca \
        mingw-w64-"${ARCH}"-libwebp || true

    if [ "${PYTHON_ID}" = "python2" ]; then
        build_pacman --noconfirm -Rdd mingw-w64-"${ARCH}"-python3 || true
    else
        build_pacman --noconfirm -Rdd mingw-w64-"${ARCH}"-python2 || true
    fi

    build_pacman --noconfirm -R $(build_pacman -Qdtq)
    build_pacman -S --noconfirm mingw-w64-"${ARCH}"-"${PYTHON_ID}"-setuptools

    wget "https://github.com/electron/node-rcedit/raw/73d4e74"`
        `"b4b406d54410faa9211900cf2a4962df5/bin/rcedit.exe"
    echo "42649d92e1bbb3af1186fb0ad063df9fcdc18e7b5f2ea8219"`
        `"1ecc8fdfaffb0d8 rcedit.exe" | sha256sum.exe -c
    mv "rcedit.exe" "${BUILD_ROOT}"
}

install_quodlibet() {
    git clone https://github.com/quodlibet/quodlibet.git "${REPO_CLONE}"
    build_python "${REPO_CLONE}"/quodlibet/setup.py install \
        --old-and-unmanageable
}

post_install() {
    local MINGW_ROOT="${BUILD_ROOT}/${MINGW}"

    # make loader loading relocatable
    # (hacky... but I don't understand the win/unix path translation magic)
    GDK_PIXBUF_PREFIX=$(cd "${BUILD_ROOT}" && \
        /"${MINGW}"/bin/"${PYTHON_ID}".exe \
        -c "import os; print os.getcwd()")"/${MINGW}"
    loaders_cache="${MINGW_ROOT}"/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache
    sed -i "s|$GDK_PIXBUF_PREFIX|..|g" "$loaders_cache"

    # make the launchers relocatable
    for i in "${MINGW_ROOT}"/bin/*-script.pyw; do
        sed -i "s|#!.*|#!${PYTHON_ID}w.exe|g" "$i"
    done

    for i in "${MINGW_ROOT}"/bin/*-script.py; do
        sed -i "s|#!.*|#!${PYTHON_ID}.exe|g" "$i"
    done

    # remove the large png icons, they should be used rarely and svg works fine
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/256x256"
    "${MINGW_ROOT}"/bin/gtk-update-icon-cache-3.0.exe \
        "${MINGW_ROOT}"/share/icons/Adwaita

    # we installed our app icons into hicolor
    "${MINGW_ROOT}"/bin/gtk-update-icon-cache-3.0.exe \
        "${MINGW_ROOT}"/share/icons/hicolor

    # set launcher icons
    # (copy things around since rcedit.exe can't handle paths)
    cp "${DIR}"/quodlibet.ico "${MINGW_ROOT}"/bin
    cp "${DIR}"/exfalso.ico "${MINGW_ROOT}"/bin
    (cd "${MINGW_ROOT}"/bin &&
     "${BUILD_ROOT}"/rcedit.exe quodlibet.exe --set-icon quodlibet.ico)
    (cd "${MINGW_ROOT}"/bin &&
     "${BUILD_ROOT}"/rcedit.exe exfalso.exe --set-icon exfalso.ico)
    rm "${MINGW_ROOT}"/bin/*.ico
}

cleanup_install() {
    local MINGW_ROOT="${BUILD_ROOT}/${MINGW}"

    # delete translations we don't support
    for d in "${MINGW_ROOT}"/share/locale/*/LC_MESSAGES; do
        if [ ! -f "${d}"/quodlibet.mo ]; then
            rm -Rf "${d}"
        fi
    done

    find "${MINGW_ROOT}" -regextype "posix-extended" -name "*.exe" -a ! \
        -iregex ".*/(quodlibet|exfalso|operon|python)[^/]*\\.exe" \
        -exec rm -f {} \;

    rm -Rf "${MINGW_ROOT}"/libexec
    rm -Rf "${MINGW_ROOT}"/share/gtk-doc
    rm -Rf "${MINGW_ROOT}"/include
    rm -Rf "${MINGW_ROOT}"/var
    rm -Rf "${MINGW_ROOT}"/etc
    rm -Rf "${MINGW_ROOT}"/share/zsh
    rm -Rf "${MINGW_ROOT}"/share/pixmaps
    rm -Rf "${MINGW_ROOT}"/share/gnome-shell
    rm -Rf "${MINGW_ROOT}"/share/dbus-1
    rm -Rf "${MINGW_ROOT}"/share/gir-1.0
    rm -Rf "${MINGW_ROOT}"/share/doc
    rm -Rf "${MINGW_ROOT}"/share/man
    rm -Rf "${MINGW_ROOT}"/share/info
    rm -Rf "${MINGW_ROOT}"/share/mime
    rm -Rf "${MINGW_ROOT}"/share/gettext
    rm -Rf "${MINGW_ROOT}"/share/libtool
    rm -Rf "${MINGW_ROOT}"/share/licenses
    rm -Rf "${MINGW_ROOT}"/share/appdata
    rm -Rf "${MINGW_ROOT}"/share/aclocal
    rm -Rf "${MINGW_ROOT}"/share/ffmpeg
    rm -Rf "${MINGW_ROOT}"/share/vala
    rm -Rf "${MINGW_ROOT}"/share/readline
    rm -Rf "${MINGW_ROOT}"/share/icons/Adwaita/cursors
    rm -Rf "${MINGW_ROOT}"/share/xml
    rm -Rf "${MINGW_ROOT}"/share/bash-completion
    rm -Rf "${MINGW_ROOT}"/share/common-lisp
    rm -Rf "${MINGW_ROOT}"/share/emacs
    rm -Rf "${MINGW_ROOT}"/share/gdb
    rm -Rf "${MINGW_ROOT}"/share/libcaca
    rm -Rf "${MINGW_ROOT}"/share/gettext
    rm -Rf "${MINGW_ROOT}"/share/gst-plugins-base
    rm -Rf "${MINGW_ROOT}"/share/gtk-3.0
    rm -Rf "${MINGW_ROOT}"/share/nghttp2
    rm -Rf "${MINGW_ROOT}"/share/themes
    rm -Rf "${MINGW_ROOT}"/share/fontconfig
    rm -Rf "${MINGW_ROOT}"/share/gettext-*
    rm -Rf "${MINGW_ROOT}"/share/gstreamer-1.0

    find "${MINGW_ROOT}"/share/glib-2.0 -type f ! \
        -name "*.compiled" -exec rm -f {} \;

    rm -Rf "${MINGW_ROOT}"/lib/"${PYTHON_ID}".*/test
    rm -Rf "${MINGW_ROOT}"/lib/cmake
    rm -Rf "${MINGW_ROOT}"/lib/gettext
    rm -Rf "${MINGW_ROOT}"/lib/gtk-3.0
    rm -Rf "${MINGW_ROOT}"/lib/mpg123
    rm -Rf "${MINGW_ROOT}"/lib/p11-kit
    rm -Rf "${MINGW_ROOT}"/lib/ruby

    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstvpx.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstdaala.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstdvdread.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopenal.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopenexr.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopenh264.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstresindvd.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstassrender.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstx265.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstwebp.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopengl.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstmxf.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstfaac.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstschro.dll

    rm -f "${MINGW_ROOT}"/bin/libharfbuzz-icu-0.dll
    rm -f "${MINGW_ROOT}"/lib/python2.*/lib-dynload/_tkinter.pyd
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstcacasink.dll

    find "${MINGW_ROOT}" -name "*.a" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.whl" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.h" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.la" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.sh" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.jar" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.def" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.cmd" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.cmake" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.pc" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.desktop" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.manifest" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.pyo" -exec rm -f {} \;

    find "${MINGW_ROOT}"/bin -name "*-config" -exec rm -f {} \;
    find "${MINGW_ROOT}"/bin -name "easy_install*" -exec rm -f {} \;
    find "${MINGW_ROOT}" -regex ".*/bin/[^.]+" -exec rm -f {} \;

    find "${MINGW_ROOT}" -name "gtk30-properties.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "gettext-tools.mo" -exec rm -rf {} \;

    find "${MINGW_ROOT}" -name "old_root.pem" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "weak.pem" -exec rm -rf {} \;

    find "${MINGW_ROOT}"/lib/"${PYTHON_ID}".* -type d -name "test*" \
        -prune -exec rm -rf {} \;

    find "${MINGW_ROOT}"/lib/"${PYTHON_ID}".* -type d -name "*_test*" \
        -prune -exec rm -rf {} \;

    "${MINGW_ROOT}"/bin/"${PYTHON_ID}".exe -m compileall -q "${MINGW_ROOT}"
    find "${MINGW_ROOT}" -name "*.py" -a ! -name "*-script.py*" \
        -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*-script.pyc" -exec rm -f {} \;

    "${MINGW_ROOT}"/bin/"${PYTHON_ID}".exe "${DIR}/depcheck.py"

    find "${MINGW_ROOT}" -type d -empty -delete
}

build_installer() {
    makensis win_installer.nsi
}

main() {
    # started from the wrong env -> switch
    if [ $(echo "$MSYSTEM" | tr '[A-Z]' '[a-z]') != "$MINGW" ]; then
        "/${MINGW}.exe" "$0"
        exit $?
    fi

    [[ -d "${BUILD_ROOT}" ]] && (echo "${BUILD_ROOT} already exists"; exit 1)
    create_root
    install_deps
    install_quodlibet
    post_install
    cleanup_install
    build_installer
}

main
