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


PYGI_AIO_VER="3.14.0_rev12"
MUTAGEN_VER="1.31"


function download_and_verify {
    # download all installers and check with sha256sum

    local FILEHASHES="\
7f6507d400d07edfd1ea8205da36808009b0c539f5b8a6e0ab54337b955e6dc3  feedparser-5.1.3.tar.bz2
d7e78da2251a35acd14a932280689c57ff9499a474a448ae86e6c43b882692dd  Git-1.9.5-preview20141217.exe
0aa011707785fe30935d8655380052a20ba8b972aa738d4f144c457b35b4d699  mutagen-$MUTAGEN_VER.tar.gz
69c2ae5c9f2ee45b0626905faffaa86d4e2fc0d3e8c118c8bc6899df68467b32  nsis-2.46-setup.exe
610a8800de3d973ed5ed4ac505ab42ad058add18a68609ac09e6cf3598ef056c  py2exe-0.6.9.win32-py2.7.exe
690698f42193330e363a0d38abf76962015459f12d38c320248c8fd6a2c8ab66  pygi-aio-$PYGI_AIO_VER-setup.exe
3db9fa9adc45703589b93df05aab77bdabe985a17565b465a9e550585f85322a  pyHook-1.5.1.win32-py2.7.exe
22f8a2b3231f9f671d660f149f7e60215b1908fa09fbb832123bf12a3e20b447  python-2.7.9.msi
728fbe415da98dad5c4d462e56cf106cf50cc28eb6a9f46b8ebabc3029f37fb9  python-musicbrainz2-0.7.4.tar.gz
dd665cca88cb059fec960516ed5f29474b33fce50fcb2633d397d4a3aa705c16  pywin32-218.win32-py2.7.exe
fe4807b4698ec89f82de7d85d32deaa4c772fc871537e31fb0fccf4473455cb8  7z920.msi
8a94f6ff1ee9562a2216d2096b87d0e54a5eb5c9391874800e5032033a1c8e85  libmodplug-1.dll
1eeedf2c29e0e7566217ba5a51aa1e3b73dfe173800fa71ac598470fbed3baf5  libgstopus.dll\
"

    mkdir -p "$BIN"
    if (cd "$BIN" && echo "$FILEHASHES" | sha256sum --status --strict -c -); then
        echo "all installers here, continue.."
    else
        wget -P "$BIN" -c http://downloads.sourceforge.net/project/nsis/NSIS%202/2.46/nsis-2.46-setup.exe
        wget -P "$BIN" -c https://github.com/msysgit/msysgit/releases/download/Git-1.9.5-preview20141217/Git-1.9.5-preview20141217.exe
        wget -P "$BIN" -c http://downloads.sourceforge.net/project/py2exe/py2exe/0.6.9/py2exe-0.6.9.win32-py2.7.exe
        wget -P "$BIN" -c "http://bitbucket.org/lazka/quodlibet/downloads/pygi-aio-$PYGI_AIO_VER-setup.exe"
        wget -P "$BIN" -c http://downloads.sourceforge.net/project/pyhook/pyhook/1.5.1/pyHook-1.5.1.win32-py2.7.exe
        wget -P "$BIN" -c http://downloads.sourceforge.net/project/pywin32/pywin32/Build%20218/pywin32-218.win32-py2.7.exe
        wget -P "$BIN" -c http://www.python.org/ftp/python/2.7.9/python-2.7.9.msi
        wget -P "$BIN" -c http://downloads.sourceforge.net/sevenzip/7z920.msi
        wget -P "$BIN" -c https://bitbucket.org/lazka/quodlibet/downloads/libmodplug-1.dll
        wget -P "$BIN" -c http://ftp.musicbrainz.org/pub/musicbrainz/python-musicbrainz2/python-musicbrainz2-0.7.4.tar.gz
        wget -P "$BIN" -c http://bitbucket.org/lazka/quodlibet/downloads/libgstopus.dll

        pip install --download="$BIN" "mutagen==$MUTAGEN_VER"
        pip install --download="$BIN" feedparser==5.1.3

        # check again
        (cd "$BIN" && echo "$FILEHASHES" |  sha256sum --strict -c -) || exit
    fi
}

function init_wine {
    # set up wine environ
    export WINEARCH=win32
    export WINEPREFIX="$BUILD_ENV"/wine_env
    export WINEDEBUG=-all

    # try to limit the effect on the host system when installing with wine.
    export HOME="$BUILD_ENV"/home
    export XDG_DATA_HOME="$HOME"/.local/share
    export XDG_CONFIG_HOME="$HOME"/.config
    export XDG_CACHE_HOME="$HOME"/.cache
    export DISPLAY_SAVED=$DISPLAY
    export DISPLAY=be_quiet_damnit

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
        cp -RT "$PYGI"/"$name"/Base/gnome "$DEPS"

        cp -RT "$PYGI"/"$name"/JPEG/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/WebP/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/Jasper/gnome "$DEPS"

        cp -RT "$PYGI"/"$name"/GDK/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/GDKPixbuf/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/ATK/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/Pango/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/GTK/gnome "$DEPS"

        cp -RT "$PYGI"/"$name"/Gstreamer/gnome "$DEPS"

        cp -RT "$PYGI"/"$name"/Orc/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/GnuTLS/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/Aerial/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/Soup/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/Jack/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/SQLite/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/GSTPlugins/gnome "$DEPS"

        cp -RT "$PYGI"/"$name"/OpenJPEG/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/OpenEXR/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/Curl/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/IDN/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/GSTPluginsExtra/gnome "$DEPS"
        cp -RT "$PYGI"/"$name"/GSTPluginsMore/gnome "$DEPS"
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

    # copy old libgstopus
    # https://github.com/quodlibet/quodlibet/issues/1511
    cp "$BUILD_ENV/bin/libgstopus.dll" "$DEPS"/lib/gstreamer-1.0
}

function install_python {
    wine msiexec /a "$BUILD_ENV"/bin/python-2.7.9.msi /qb
    PYDIR="$WINEPREFIX"/drive_c/Python27

    # install the python packages
    local SITEPACKAGES="$PYDIR"/Lib/site-packages
    cp -R "$PYGI"/binding/py2.7-32/cairo "$SITEPACKAGES"
    cp -R "$PYGI"/binding/py2.7-32/gi "$SITEPACKAGES"
    cp "$PYGI"/binding/py2.7-32/*.pyd "$SITEPACKAGES"
}

function install_git {
    local DISPLAY_OLD=$DISPLAY
    export DISPLAY=$DISPLAY_SAVED
    # this needs a valid DISPLAY..
    wine "$BUILD_ENV"/bin/Git-1.9.5-preview20141217.exe /VERYSILENT;
    export DISPLAY=$DISPLAY_OLD
    GITDIR="$(winepath -u "$(wine cmd.exe /c 'echo | set /p=%ProgramFiles%')")/Git";
}

function install_7zip {
    wine msiexec /a "$BUILD_ENV"/bin/7z920.msi /qb
    SZIPDIR="$WINEPREFIX/drive_c/Program Files/7-Zip/"
}

function install_nsis {
    wine "$BUILD_ENV"/bin/nsis-2.46-setup.exe /S
}

function install_pydeps {
    local PYTHON="$PYDIR"/python.exe
    (
    cd "$BUILD_ENV"/bin
    wine $PYTHON -m pip install "mutagen-$MUTAGEN_VER.tar.gz"
    wine $PYTHON -m pip install feedparser-5.1.3.tar.bz2
    wine $PYTHON -m pip install python-musicbrainz2-0.7.4.tar.gz
    wine $PYTHON -m easy_install -Z pywin32-218.win32-py2.7.exe
    wine $PYTHON -m easy_install -Z py2exe-0.6.9.win32-py2.7.exe
    wine $PYTHON -m easy_install -Z pyHook-1.5.1.win32-py2.7.exe
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
    local NSIS_PATH=$(winepath "C:\\Program Files\\NSIS\\")
    # now package everything up
    (cd "$BUILD_ENV" && wine "$NSIS_PATH/makensis.exe" win_installer.nsi)
    mv "$BUILD_ENV/quodlibet-LATEST.exe" "$DIR/quodlibet-$QL_VERSION-installer.exe"
}

function package_portable_installer {
    local PORTABLE="$BUILD_ENV/quodlibet-$QL_VERSION-portable"
    mkdir "$PORTABLE"

    cp "$MISC"/quodlibet.lnk "$PORTABLE"
    cp "$MISC"/exfalso.lnk "$PORTABLE"
    cp "$MISC"/README-PORTABLE.txt "$PORTABLE"/README.txt
    mkdir "$PORTABLE"/config
    PORTABLE_DATA="$PORTABLE"/data
    mkdir "$PORTABLE_DATA"
    cp -RT "$QL_DEST" "$PORTABLE_DATA"
    cp "$MISC"/conf.py "$PORTABLE_DATA"/bin/quodlibet/

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
    tar --dereference -zcvf "$DIR"/quodlibet-win-sdk.tar.gz _sdk/ \
        --exclude=_sdk/quodlibet \
        --exclude=_sdk/_wine_prefix \
        --exclude=_sdk/_ql_config &> /dev/null
}


function cleanup {
    # no longer needed, save disk space
    rm -Rf "$PYGI"
}
