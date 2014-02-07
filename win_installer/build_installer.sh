#!/bin/bash
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

###############################################################################

HG_TAG="default"

###############################################################################

DIR="$( cd "$( dirname "$0" )" && pwd )"
MISC="$DIR"/misc
BIN="$DIR"/_bin

# download all installers and check with sha256sum
mkdir -p "$BIN"
cd "$BIN"

if sha256sum -c "$MISC"/filehashes.txt; then
    echo "all installers here, continue.."
else
    wget -c https://bitbucket.org/pypa/setuptools/raw/2.1.1/ez_setup.py
    wget -c http://mercurial.selenic.com/release/windows/mercurial-2.8.1-x86.msi
    wget -c http://downloads.sourceforge.net/project/nsis/NSIS%202/2.46/nsis-2.46-setup.exe
    wget -c http://downloads.sourceforge.net/project/py2exe/py2exe/0.6.9/py2exe-0.6.9.win32-py2.7.exe
    wget -c http://downloads.sourceforge.net/project/pygobjectwin32/pygi-aio-3.10.2-win32_rev17-setup.exe
    wget -c http://downloads.sourceforge.net/project/pyhook/pyhook/1.5.1/pyHook-1.5.1.win32-py2.7.exe
    wget -c http://downloads.sourceforge.net/project/pywin32/pywin32/Build%20218/pywin32-218.win32-py2.7.exe
    wget -c http://www.python.org/ftp/python/2.7.6/python-2.7.6.msi
    wget -c http://downloads.sourceforge.net/sevenzip/7z920.msi
    wget -c https://bitbucket.org/lazka/quodlibet/downloads/libmodplug-1.dll

    pip install --download=. mutagen==1.22
    pip install --download=. feedparser==5.1.3
    pip install --download=. python-musicbrainz2==0.7.4

    # check again
    sha256sum -c "$MISC"/filehashes.txt || exit
fi

cd "$DIR"

# start building
QL_REPO="$DIR"/..
BUILD_BAT="$MISC"/build.bat
PACKAGE_BAT="$MISC"/package.bat
INST_ICON="$MISC"/quodlibet.ico
NSIS_SCRIPT="$MISC"/win_installer.nsi
BUILD_ENV="$DIR"/_build_env
QL_TEMP="$BUILD_ENV"/ql_temp

# set up wine cfg
export WINEARCH=win32
export WINEPREFIX="$BUILD_ENV"/wine_env
export WINEDEBUG=-all

# try to limit the effect on the host system when installing with wine.
# desktop links still get installed. :/
export WINEDLLOVERRIDES="winemenubuilder.exe=d"

# create a fresh build env and link the binaries in
rm -Rf "$BUILD_ENV"
mkdir "$BUILD_ENV"
cd "$BUILD_ENV"
ln -s "$BIN" bin

# clone repo, create translations
hg clone "$QL_REPO" "$QL_TEMP"
cd "$QL_TEMP"
hg up "$HG_TAG"
cd "quodlibet"
python setup.py build_mo
QL_VERSION=$(python -c "import quodlibet.const;print quodlibet.const.VERSION,")

# link the batch file and nsis file in
cd "$BUILD_ENV"
ln -s "$BUILD_BAT"
ln -s "$PACKAGE_BAT"
ln -s "$NSIS_SCRIPT"
ln -s "$INST_ICON"

# extract the gi binaries
PYGI="$BUILD_ENV"/pygi
7z x -o"$PYGI" -y bin/pygi-aio-3.10.2-win32_rev17-setup.exe > /dev/null
cd "$PYGI"/rtvc9/
find . -name "*.7z" -execdir 7z x -y {} > /dev/null \;
cd "$PYGI"/binding/py2.7
7z x -y py2.7.7z > /dev/null
cd "$BUILD_ENV"

# prepare our binary deps
DEPS="$BUILD_ENV"/deps
mkdir "$DEPS"

cp "$PYGI"/binding/py2.7/gnome/*.dll "$DEPS"

cp -RT "$PYGI"/rtvc9/Base/gnome "$DEPS" #ok

cp -RT "$PYGI"/rtvc9/JPEG/gnome "$DEPS" #ok
cp -RT "$PYGI"/rtvc9/WebP/gnome "$DEPS" # ok

cp -RT "$PYGI"/rtvc9/GDK/gnome "$DEPS" #ok
cp -RT "$PYGI"/rtvc9/GDKPixbuf/gnome "$DEPS" #pk
cp -RT "$PYGI"/rtvc9/ATK/gnome "$DEPS" #ok
cp -RT "$PYGI"/rtvc9/Pango/gnome "$DEPS" #ok
cp -RT "$PYGI"/rtvc9/GTK/gnome "$DEPS" #ok

cp -RT "$PYGI"/rtvc9/Gstreamer/gnome "$DEPS" #ok

cp -RT "$PYGI"/rtvc9/Orc/gnome "$DEPS"
cp -RT "$PYGI"/rtvc9/GnuTLS/gnome "$DEPS"
cp -RT "$PYGI"/rtvc9/Soup/gnome "$DEPS"
cp -RT "$PYGI"/rtvc9/SQLite/gnome "$DEPS"
cp -RT "$PYGI"/rtvc9/GSTPlugins/gnome "$DEPS"

cp -RT "$PYGI"/rtvc9/OpenJPEG/gnome "$DEPS"
cp -RT "$PYGI"/rtvc9/Nice/gnome "$DEPS"
cp -RT "$PYGI"/rtvc9/Curl/gnome "$DEPS"
cp -RT "$PYGI"/rtvc9/GSTPluginsExtra/gnome "$DEPS"

# create the icon theme caches
wine "$DEPS"/gtk-update-icon-cache.exe "$DEPS"/share/icons/gnome
wine "$DEPS"/gtk-update-icon-cache.exe "$DEPS"/share/icons/hicolor
wine "$DEPS"/gtk-update-icon-cache.exe "$DEPS"/share/icons/HighContrast

# set gtk settings etc.
GTK_SETTINGS="$DEPS"/etc/gtk-3.0/settings.ini
echo "[Settings]" > "$GTK_SETTINGS"
echo "gtk-theme-name = Adwaita" >> "$GTK_SETTINGS"
echo "gtk-fallback-icon-theme = gnome" >> "$GTK_SETTINGS"
echo "gtk-xft-antialias = 1" >> "$GTK_SETTINGS"
echo "gtk-xft-dpi = 98304" >> "$GTK_SETTINGS"
echo "gtk-xft-hinting = 1" >> "$GTK_SETTINGS"
echo "gtk-xft-hintstyle = hintfull" >> "$GTK_SETTINGS"
echo "gtk-xft-rgba = rgb" >> "$GTK_SETTINGS"

# copy libmodplug
cp "bin/libmodplug-1.dll" "$DEPS"

# now install python etc.
wine msiexec /a bin/python-2.7.6.msi /qb
wine msiexec /a bin/7z920.msi /qb
wine bin/nsis-2.46-setup.exe /S

PYDIR="$WINEPREFIX"/drive_c/Python27
SZIPDIR="$WINEPREFIX/drive_c/Program Files/7-Zip/"

# install the python packages
SITEPACKAGES="$PYDIR"/Lib/site-packages

cp -R "$PYGI"/binding/py2.7/cairo "$SITEPACKAGES"
cp -R "$PYGI"/binding/py2.7/gi "$SITEPACKAGES"
cp "$PYGI"/binding/py2.7/*.pyd "$SITEPACKAGES"

# now run py2exe etc.
wine cmd /c build.bat

QL_DEST="$QL_TEMP"/quodlibet/dist
QL_BIN="$QL_DEST"/bin

# python dlls
cp "$PYDIR"/python27.dll "$QL_BIN"

# copy deps
cp "$DEPS"/*.dll "$QL_BIN"
cp -R "$DEPS"/etc "$QL_DEST"
cp -R "$DEPS"/lib "$QL_DEST"
cp -R "$DEPS"/share "$QL_DEST"

# remove translatins we don't support
QL_LOCALE="$QL_TEMP"/quodlibet/build/share/locale
MAIN_LOCALE="$QL_DEST"/share/locale
python "$MISC"/prune_translations.py "$QL_LOCALE" "$MAIN_LOCALE"

# copy the translations
cp -RT "$QL_LOCALE" "$MAIN_LOCALE"
# remove the gtk30-properties domain -> not visible to the user
find "$MAIN_LOCALE" -name "gtk30-properties.mo" -exec rm {} \;

# copy plugins; byte compile them; remove leftover *.py files
cp -RT "$QL_TEMP"/plugins "$QL_BIN"/quodlibet/plugins
wine "$PYDIR"/python.exe -m compileall $(wine winepath -w "$QL_BIN"/quodlibet/plugins)
find "$QL_DEST" -name "*.py" | xargs -I {} rm -v "{}"

# remove gtk themes except HighContrast/Adwaita/Default
GTK_THEMES="$QL_DEST"/share/themes
rm -Rf "$GTK_THEMES"/DeLorean
rm -Rf "$GTK_THEMES"/Emacs
rm -Rf "$GTK_THEMES"/Evolve
rm -Rf "$GTK_THEMES"/Greybird

# remove ladspa, frei0r
rm -Rf "$QL_DEST"/lib/frei0r-1
rm -Rf "$QL_DEST"/lib/ladspa-1

# remove some large gstreamer plugins..
GST_LIBS="$QL_DEST"/lib/gstreamer-1.0
rm "$GST_LIBS"/libgstflite.dll # Flite speech synthesizer plugin
rm "$GST_LIBS"/libgstopencv.dll # OpenCV Plugins
rm "$GST_LIBS"/libgstx264.dll # H264 plugins
rm "$GST_LIBS"/libgstcacasink.dll # Colored ASCII Art video sink
rm "$GST_LIBS"/libgstschro.dll # Schroedinger plugin
rm "$GST_LIBS"/libgstjack.dll # Jack sink/source
rm "$GST_LIBS"/libgstpulse.dll # Pulse sink
rm "$GST_LIBS"/libgstvpx.dll # VP8

# and some other stuff we don't need
rm -R "$QL_DEST"/share/gst-plugins-bad

# now package everything up
cd "$BUILD_ENV"
wine cmd /c package.bat
mv "quodlibet-LATEST.exe" "$DIR/quodlibet-$QL_VERSION-installer.exe"

###############################################
# Portable version

PORTABLE="$BUILD_ENV/quodlibet-$QL_VERSION-portable"
mkdir "$PORTABLE"

cp "$MISC"/quodlibet.lnk "$PORTABLE"
cp "$MISC"/exfalso.lnk "$PORTABLE"
cp "$MISC"/README-PORTABLE.txt "$PORTABLE"/README.txt
mkdir "$PORTABLE"/config
PORTABLE_DATA="$PORTABLE"/data
mkdir "$PORTABLE_DATA"
cp -RT "$QL_DEST" "$PORTABLE_DATA"
cp "$MISC"/conf.py "$PORTABLE_DATA"/bin/quodlibet/

wine "$SZIPDIR"/7z.exe a portable-temp.7z "$PORTABLE"
cat "$SZIPDIR"/7z.sfx portable-temp.7z > "quodlibet-$QL_VERSION-portable.exe"
rm portable-temp.7z
mv "quodlibet-$QL_VERSION-portable.exe" "$DIR"

###############################################
# Now the SDK

SDK="$BUILD_ENV"/quodlibet-win-sdk
mkdir "$SDK"

# launchers, README
cp "$MISC"/env.bat "$SDK"
cp "$MISC"/wine.sh "$SDK"
cp "$MISC"/README-SDK.txt "$SDK"/README.txt

# bin deps
cp -R "$DEPS" "$SDK"
cp -R "$PYDIR" "$SDK"
mv "$SDK"/Python27 "$SDK"/python

# clone again
QL_SDK="$SDK"/quodlibet
hg clone "$QL_REPO" "$QL_SDK"
# copy the remote
cp -f "$QL_REPO"/.hg/hgrc "$QL_SDK"/.hg/

# link in the plugins
QL_SDK_CONFIG="$SDK"/_ql_config
mkdir "$QL_SDK_CONFIG"
cd "$QL_SDK_CONFIG"
ln -s ../quodlibet/plugins

# done, hurray!
echo "DONE!"
