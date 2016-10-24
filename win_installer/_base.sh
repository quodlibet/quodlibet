#!/bin/bash
# Copyright 2013-2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

trap 'exit 1' SIGINT;

DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$DIR"

MISC="$DIR"/misc
BIN="$DIR"/_bin
QL_REPO="$DIR"/..
BUILD_BAT="$MISC"/build.bat
INST_ICON="$MISC"/quodlibet.ico
NSIS_SCRIPT="$MISC"/win_installer.nsi
BUILD_ENV="$DIR"/_build_env"$BUILD_ENV_SUFFIX"
QL_REPO_TEMP="$BUILD_ENV"/ql_temp
QL_TEMP="$QL_REPO_TEMP"/quodlibet


PYGI_AIO_VER="3.18.2_rev9"
MUTAGEN_VER="1.34.1"
BUILD_VERSION="0"


function download_and_verify {
    # download all installers and check with sha256sum

    local FILEHASHES="\
0542525145d5afc984c88f914a0c85c77527f65946617edb5274f72406f981df  futures-3.0.5.tar.gz
cd2485472e41471632ed3029d44033ee420ad0b57111db95c240c9160a85831c  feedparser-5.2.1.zip
f7708a42d86f29ccc7c8c4ff9d34a8d854d8d78eb2973d1f28406bb43d6b8919  certifi-2016.8.31.tar.gz
d7e78da2251a35acd14a932280689c57ff9499a474a448ae86e6c43b882692dd  Git-1.9.5-preview20141217.exe
aacd667ef1f4fa7b7c201f36b2a6eda1ead3c92331017601d8082af62a7ee461  mutagen-$MUTAGEN_VER.tar.gz
8a4a86bd028793038a4b744281a4df436948f3d1941adcb68c07ba6e42fb6165  nsis-2.51-setup.exe
610a8800de3d973ed5ed4ac505ab42ad058add18a68609ac09e6cf3598ef056c  py2exe-0.6.9.win32-py2.7.exe
69e1e2786e4bd49fcd85d7310b5dd716393a5b8152877d431bfc8f18b7677d73  pygi-aio-$PYGI_AIO_VER-setup.exe
3ac291535bcf15fd5a15bcd29b066570e8d2a0cab4f3b92a2372f41aa09a4f48  python-2.7.12.msi
ec447bcab906fe7c4dbd714a1dff1b00adcd20d0011968df1a740e6b1fb09cb5  python-musicbrainzngs-0.6.tar.gz
12c18abb9a09a5b2802dba75c7a2d7d6c8c0f1258abd8243e7688415d87ad1d8  pytest-2.9.2.tar.gz
a6501963c725fc2554dabfece8ae9a8fb5e149c0ac0a42fd2b02c5c1c57fc114  py-1.4.31.tar.gz
f4945bf52ae49da0728fe730a33c18744803752fc948f154f29dc0c4f9f2f9cc  colorama-0.3.7.zip
547c24748705ad4b6e3f3944f38d0416c5cdd2de6ebe3d65a1840bd2b82519a4  7z1602.msi
8a94f6ff1ee9562a2216d2096b87d0e54a5eb5c9391874800e5032033a1c8e85  libmodplug-1.dll\
"

    mkdir -p "$BIN"
    if (cd "$BIN" && echo "$FILEHASHES" | sha256sum --status --strict -c -); then
        echo "all installers here, continue.."
    else
        wget -P "$BIN" -c http://downloads.sourceforge.net/project/nsis/NSIS%202/2.51/nsis-2.51-setup.exe
        wget -P "$BIN" -c https://github.com/msysgit/msysgit/releases/download/Git-1.9.5-preview20141217/Git-1.9.5-preview20141217.exe
        wget -P "$BIN" -c http://downloads.sourceforge.net/project/py2exe/py2exe/0.6.9/py2exe-0.6.9.win32-py2.7.exe
        wget -P "$BIN" -c "http://bitbucket.org/lazka/quodlibet/downloads/pygi-aio-$PYGI_AIO_VER-setup.exe"
        wget -P "$BIN" -c http://www.python.org/ftp/python/2.7.12/python-2.7.12.msi
        wget -P "$BIN" -c http://downloads.sourceforge.net/sevenzip/7z1602.msi
        wget -P "$BIN" -c https://bitbucket.org/lazka/quodlibet/downloads/libmodplug-1.dll
        wget -c http://github.com/alastair/python-musicbrainzngs/archive/v0.6.tar.gz -O "$BIN"/python-musicbrainzngs-0.6.tar.gz

        pip download --dest="$BIN" --no-deps --no-binary=":all:" "mutagen==$MUTAGEN_VER"
        pip download --dest="$BIN" --no-deps --no-binary=":all:" "feedparser==5.2.1"
        pip download --dest="$BIN" --no-deps --no-binary=":all:" "certifi==2016.8.31"
        pip download --dest="$BIN" --no-deps --no-binary=":all:" "pytest==2.9.2"
        pip download --dest="$BIN" --no-deps --no-binary=":all:" "py==1.4.31"
        pip download --dest="$BIN" --no-deps --no-binary=":all:" "colorama==0.3.7"
        pip download --dest="$BIN" --no-deps --no-binary=":all:" "futures==3.0.5"

        # check again
        (cd "$BIN" && echo "$FILEHASHES" |  sha256sum --strict -c -) || exit
    fi
}

function init_wine {
    # set up wine environ
    export WINEARCH=win32
    export WINEPREFIX="$BUILD_ENV"/wine_env
    export WINEDEBUG=-all
    export WINEDLLOVERRIDES="mscoree,mshtml="

    # try to limit the effect on the host system when installing with wine.
    export HOME="$BUILD_ENV"/home
    export XDG_DATA_HOME="$HOME"/.local/share
    export XDG_CONFIG_HOME="$HOME"/.config
    export XDG_CACHE_HOME="$HOME"/.cache

    mkdir -p "$WINEPREFIX"
    wine wineboot -u
}

function init_build_env {
    # create a fresh build env and link the binaries in
    rm -Rf "$BUILD_ENV"
    mkdir "$BUILD_ENV"
    ln -s "$BIN" "$BUILD_ENV"/bin

    # link the batch file and nsis file in
    ln -s "$BUILD_BAT" "$BUILD_ENV"
    ln -s "$NSIS_SCRIPT" "$BUILD_ENV"
    ln -s "$INST_ICON" "$BUILD_ENV"
}

# Argument 1: the git tag
function clone_repo {

    if [ -z "$1" ]
    then
        echo "missing arg"
        exit 1
    fi

    # clone repo
    git clone "$QL_REPO" "$QL_REPO_TEMP"
    (cd "$QL_REPO_TEMP" && git checkout "$1") || exit 1
    QL_VERSION=$(cd "$QL_TEMP" && python -c "import quodlibet.const;print quodlibet.const.VERSION,")

    if [ "$1" = "master" ]
    then
        local GIT_REV=$(git rev-list --count HEAD)
        local GIT_HASH=$(git rev-parse --short HEAD)
        QL_VERSION="$QL_VERSION-rev$GIT_REV-$GIT_HASH"
    fi
}

function extract_deps {
    # extract the gi binaries
    PYGI="$BUILD_ENV"/pygi
    echo "extract pygi-aio..."
    7z x -o"$PYGI" -y "$BUILD_ENV/bin/pygi-aio-$PYGI_AIO_VER-setup.exe" > /dev/null
    echo "done"
    echo "extract packages..."
    (cd "$PYGI"/rtvc9-32/ && find . -name "*.7z" -execdir 7z x -y {} > /dev/null \;)
    (cd "$PYGI"/noarch/ && find . -name "*.7z" -execdir 7z x -y {} > /dev/null \;)
    (cd "$PYGI"/binding/py2.7-32 && 7z x -y py2.7-32.7z > /dev/null)
    echo "done"

    # prepare our binary deps
    DEPS="$BUILD_ENV"/deps
    mkdir "$DEPS"

    for name in rtvc9-32 noarch; do
        for package in ATK Aerial Base Curl GCrypt GDK GDKPixbuf GSTPlugins \
            GSTPluginsExtra GSTPluginsMore GTK GnuTLS Graphene Gstreamer \
            HarfBuzz Heimdal IDN JPEG Jack LibAV OpenEXR OpenJPEG OpenSSL Orc \
            Pango SQLite Soup StdCPP TIFF WebP; do
        cp -RT "$PYGI"/"$name"/"$package"/gnome "$DEPS"
        done
    done

    # remove ladspa, frei0r
    rm -Rf "$DEPS"/lib/frei0r-1
    rm -Rf "$DEPS"/lib/ladspa

    # remove opencv
    rm -Rf "$DEPS"/share/opencv

    # other stuff
    rm -Rf "$DEPS"/lib/gst-validate-launcher
    rm -Rf "$DEPS"/lib/gdbus-2.0
    rm -Rf "$DEPS"/lib/p11-kit

    # remove some large gstreamer plugins..
    GST_LIBS="$DEPS"/lib/gstreamer-1.0
    rm -f "$GST_LIBS"/libgstflite.dll # Flite speech synthesizer plugin
    rm -f "$GST_LIBS"/libgstopencv.dll # OpenCV Plugins
    rm -f "$GST_LIBS"/libgstx264.dll # H264 plugins
    rm -f "$GST_LIBS"/libgstcacasink.dll # Colored ASCII Art video sink
    rm -f "$GST_LIBS"/libgstschro.dll # Schroedinger plugin
    rm -f "$GST_LIBS"/libgstjack.dll # Jack sink/source
    rm -f "$GST_LIBS"/libgstpulse.dll # Pulse sink
    rm -f "$GST_LIBS"/libgstvpx.dll # VP8
    rm -f "$GST_LIBS"/libgstomx.dll # errors on loading
    rm -f "$GST_LIBS"/libgstdaala.dll # Daala codec
    rm -f "$GST_LIBS"/libgstmpeg2enc.dll # mpeg video encoder
    rm -f "$GST_LIBS"/libgstdeinterlace.dll # video deinterlacer
    rm -f "$GST_LIBS"/libgstopenexr.dll # OpenEXR image plugin
    rm -f "$GST_LIBS"/libgstmxf.dll # MXF Demuxer

    rm -f "$GST_LIBS"/libgstpythonplugin*.dll
}

function setup_deps {
    echo "create the icon theme caches"
    wine "$DEPS"/gtk-update-icon-cache.exe "$DEPS"/share/icons/Adwaita
    wine "$DEPS"/gtk-update-icon-cache.exe "$DEPS"/share/icons/hicolor
    wine "$DEPS"/gtk-update-icon-cache.exe "$DEPS"/share/icons/HighContrast

    echo "compile glib schemas"
    wine "$DEPS"/glib-compile-schemas.exe "$DEPS"/share/glib-2.0/schemas

    # copy libmodplug
    cp "$BUILD_ENV/bin/libmodplug-1.dll" "$DEPS"
}

function install_python {
    wine msiexec /a "$BUILD_ENV"/bin/python-2.7.12.msi /qb
    PYDIR="$WINEPREFIX"/drive_c/Python27

    # install the python packages
    local SITEPACKAGES="$PYDIR"/Lib/site-packages
    cp -R "$PYGI"/binding/py2.7-32/cairo "$SITEPACKAGES"
    cp -R "$PYGI"/binding/py2.7-32/gi "$SITEPACKAGES"
}

function install_git {
    wine "$BUILD_ENV"/bin/Git-1.9.5-preview20141217.exe /VERYSILENT;
    GITDIR="$(wine winepath -u "$(wine cmd.exe /c 'echo | set /p=%ProgramFiles%')")/Git";
}

function install_7zip {
    wine msiexec /a "$BUILD_ENV"/bin/7z1602.msi /qb
    SZIPDIR="$WINEPREFIX/drive_c/Program Files/7-Zip/"
}

function install_nsis {
    wine "$BUILD_ENV"/bin/nsis-2.51-setup.exe /S
}

function install_pydeps {
    local PYTHON="$PYDIR"/python.exe
    (
    cd "$BUILD_ENV"/bin

    wine $PYTHON -m pip install futures-3.0.5.tar.gz
    wine $PYTHON -m pip install colorama-0.3.7.zip
    wine $PYTHON -m pip install py-1.4.31.tar.gz
    wine $PYTHON -m pip install pytest-2.9.2.tar.gz
    wine $PYTHON -m pip install "mutagen-$MUTAGEN_VER.tar.gz"
    wine $PYTHON -m pip install feedparser-5.2.1.zip
    wine $PYTHON -m pip install certifi-2016.8.31.tar.gz
    wine $PYTHON -m pip install python-musicbrainzngs-0.6.tar.gz
    wine $PYTHON -m easy_install -Z py2exe-0.6.9.win32-py2.7.exe
    )
}

function build_quodlibet {
    (cd "$QL_TEMP" && python setup.py build_mo)

    # now run py2exe etc.
    (cd "$BUILD_ENV" && wine cmd /c build.bat)

    QL_DEST="$QL_TEMP"/dist
    QL_BIN="$QL_DEST"/bin

    # python dlls
    cp "$PYDIR"/python27.dll "$QL_BIN"

    # copy deps
    cp "$DEPS"/*.dll "$QL_BIN"
    cp -R "$DEPS"/etc "$QL_DEST"
    cp -R "$DEPS"/lib "$QL_DEST"
    cp -R "$DEPS"/share "$QL_DEST"

    # remove translatins we don't support
    QL_LOCALE="$QL_TEMP"/build/share/locale
    MAIN_LOCALE="$QL_DEST"/share/locale
    python "$MISC"/prune_translations.py "$QL_LOCALE" "$MAIN_LOCALE"

    # copy the translations
    cp -RT "$QL_LOCALE" "$MAIN_LOCALE"

    # remove various translations that are unlikely to be visible to the user
    # in our case and just increase the installer size
    find "$MAIN_LOCALE" -name "gtk30-properties.mo" -exec rm {} \;
    find "$MAIN_LOCALE" -name "gsettings-desktop-schemas.mo" -exec rm {} \;
    find "$MAIN_LOCALE" -name "iso_*.mo" -exec rm {} \;
}

function package_installer {
    local NSIS_PATH=$(wine winepath "C:\\Program Files\\NSIS\\")
    local PYTHON="$PYDIR"/python.exe

    # write build config
    local BUILDPY="$QL_DEST"/bin/quodlibet/build.py
    cp "$QL_TEMP"/quodlibet/build.py "$BUILDPY"
    echo 'BUILD_TYPE = u"windows"' >> "$BUILDPY"
    echo "BUILD_VERSION = $BUILD_VERSION" >> "$BUILDPY"
    (cd "$QL_TEMP" && echo "BUILD_INFO = u\"$(git rev-parse --short HEAD)\"" >> "$BUILDPY")
    (cd $(dirname "$BUILDPY") && wine "$PYTHON" -m compileall -f -l .)
    rm -f "$BUILDPY"

    # now package everything up
    (cd "$BUILD_ENV" && wine "$NSIS_PATH/makensis.exe" win_installer.nsi)
    mv "$BUILD_ENV/quodlibet-LATEST.exe" "$DIR/quodlibet-$QL_VERSION-installer.exe"
}

function package_portable_installer {
    local PORTABLE="$BUILD_ENV/quodlibet-$QL_VERSION-portable"
    local PYTHON="$PYDIR"/python.exe
    mkdir "$PORTABLE"

    cp "$MISC"/quodlibet.lnk "$PORTABLE"
    cp "$MISC"/exfalso.lnk "$PORTABLE"
    cp "$MISC"/README-PORTABLE.txt "$PORTABLE"/README.txt
    mkdir "$PORTABLE"/config
    PORTABLE_DATA="$PORTABLE"/data
    mkdir "$PORTABLE_DATA"
    cp -RT "$QL_DEST" "$PORTABLE_DATA"

    # write build config
    local BUILDPY="$PORTABLE_DATA"/bin/quodlibet/build.py
    cp "$QL_TEMP"/quodlibet/build.py "$BUILDPY"
    echo 'BUILD_TYPE = u"windows-portable"' >> "$BUILDPY"
    echo "BUILD_VERSION = $BUILD_VERSION" >> "$BUILDPY"
    (cd "$QL_TEMP" && echo "BUILD_INFO = u\"$(git rev-parse --short HEAD)\"" >> "$BUILDPY")
    (cd $(dirname "$BUILDPY") && wine "$PYTHON" -m compileall -f -l .)
    rm -f "$BUILDPY"

    wine "$SZIPDIR"/7z.exe a "$BUILD_ENV"/portable-temp.7z "$PORTABLE"
    cat "$SZIPDIR"/7z.sfx "$BUILD_ENV"/portable-temp.7z > "$DIR/quodlibet-$QL_VERSION-portable.exe"
    rm "$BUILD_ENV"/portable-temp.7z
}

function setup_sdk {
    SDK="$BUILD_ENV"/quodlibet-win-sdk
    mkdir "$SDK"

    # launchers, README
    ln -s "$MISC"/env.bat "$SDK"
    ln -s "$MISC"/test.bat "$SDK"
    ln -s "$MISC"/clone.bat "$SDK"
    ln -s "$MISC"/wine.sh "$SDK"
    ln -s "$MISC"/test.sh "$SDK"
    ln -s "$MISC"/test_ci.sh "$SDK"
    ln -s "$MISC"/README-SDK.txt "$SDK"/README.txt

    # bin deps
    ln -s "$DEPS" "$SDK"/deps
    ln -s "$PYDIR" "$SDK"/python
    ln -s "$GITDIR" "$SDK"/git

    # ql
    ln -s "$QL_REPO" "$SDK"/quodlibet

    # link to base dir
    ln -s "$SDK" "$DIR"/_sdk

    # create the distributable archive
    tar --dereference \
        --exclude=_sdk/quodlibet \
        --exclude=_sdk/_wine_prefix \
        --exclude=_sdk/_ql_config \
        -Jcvf "$DIR"/quodlibet-win-sdk.tar.xz _sdk/ \
        &> /dev/null
}


function cleanup {
    # no longer needed, save disk space
    rm -Rf "$PYGI"
}
