#!/bin/bash
# Copyright 2016,2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Pass the tag/revision to install, or install the current revision
# if nothing is passed

set -e

source env.sh
DIR="$( cd "$( dirname "$0" )" && pwd )"


function main {
    local GIT_TAG=${1:-"master"}

    jhbuild run gtk-mac-bundler misc/bundle/app.bundle

    APP="$QL_OSXBUNDLE_BUNDLE_DEST/Application.app"
    APP_PREFIX="$APP"/Contents/Resources

    # kill some useless files
    rm -f "$APP_PREFIX"/lib/python2.7/config/libpython2.7.a
    rm -Rf "$APP_PREFIX"/lib/python2.7/*/test
    rm -f "$APP"/Contents/MacOS/_launcher-bin
    rm -Rf "$APP_PREFIX"/include/
    find "$APP_PREFIX"/lib/python2.7 -name '*.pyo' -delete
    find "$APP_PREFIX"/lib/python2.7 -name '*.pyc' -delete

    # remove some larger icon theme files
    rm -Rf "${APP_PREFIX}/share/icons/Adwaita/cursors"
    rm -Rf "${APP_PREFIX}/share/icons/Adwaita/512x512"
    rm -Rf "${APP_PREFIX}/share/icons/Adwaita/256x256"
    rm -Rf "${APP_PREFIX}/share/icons/Adwaita/96x96"
    rm -Rf "${APP_PREFIX}/share/icons/Adwaita/48x48"
    jhbuild run gtk-update-icon-cache "${APP_PREFIX}/share/icons/Adwaita"

    # compile the stdlib
    jhbuild run python -m compileall -d "" -f "$APP_PREFIX"/lib/python2.7
    # delete stdlib source
    find "$APP_PREFIX"/lib/python2.7 -name '*.py' -delete

    # clone this repo and install into the bundle
    CLONE="$QL_OSXBUNDLE_BUNDLE_DEST"/_temp_clone
    git clone ../ "$CLONE"
    (cd "$CLONE"; git checkout "$GIT_TAG")
    jhbuild run "$CLONE"/quodlibet/setup.py install --prefix="$APP_PREFIX" \
        --record="$QL_OSXBUNDLE_BUNDLE_DEST"/_install_log.txt
    rm -Rf "$CLONE"

    jhbuild run python ./misc/prune_translations.py "$APP_PREFIX"/share/locale

    # create launchers
    (cd "$APP"/Contents/MacOS/ && ln -s _launcher quodlibet)
    (cd "$APP"/Contents/MacOS/ && ln -s _launcher exfalso)
    (cd "$APP"/Contents/MacOS/ && ln -s _launcher operon)
    (cd "$APP"/Contents/MacOS/ && ln -s _launcher run)
    (cd "$APP"/Contents/MacOS/ && ln -s _launcher gst-plugin-scanner)

    EXFALSO="$QL_OSXBUNDLE_BUNDLE_DEST/ExFalso.app"
    EXFALSO_PREFIX="$EXFALSO"/Contents/Resources
    QUODLIBET="$QL_OSXBUNDLE_BUNDLE_DEST/QuodLibet.app"
    QUODLIBET_PREFIX="$QUODLIBET"/Contents/Resources

    cp -R "$APP" "$EXFALSO"
    mv "$APP" "$QUODLIBET"

    echo 'BUILD_TYPE = u"osx-exfalso"' >> \
        "$EXFALSO_PREFIX"/lib/python2.7/site-packages/quodlibet/build.py
    echo 'BUILD_TYPE = u"osx-quodlibet"' >> \
        "$QUODLIBET_PREFIX"/lib/python2.7/site-packages/quodlibet/build.py

    # force compile again to get relative paths in pyc files and for the
    # modified files
    jhbuild run python -m compileall -d "" -f "$EXFALSO_PREFIX"/lib/python2.7
    jhbuild run python -m compileall -d "" -f "$QUODLIBET_PREFIX"/lib/python2.7

    VERSION=$("$QUODLIBET"/Contents/MacOS/run -c \
        "import sys, quodlibet.const;sys.stdout.write(quodlibet.const.VERSION)")
    jhbuild run python ./misc/create_info.py "quodlibet" "$VERSION" > \
        "$QUODLIBET"/Contents/Info.plist
    jhbuild run python ./misc/create_info.py "exfalso" "$VERSION" > \
        "$EXFALSO"/Contents/Info.plist

    jhbuild run python ./misc/list_content.py "$HOME/jhbuild_prefix" \
        "$QUODLIBET" > "$QUODLIBET/Contents/Resources/content.txt"
    jhbuild run python ./misc/list_content.py "$HOME/jhbuild_prefix" \
        "$EXFALSO" > "$EXFALSO/Contents/Resources/content.txt"

    DMG_SETTINGS="misc/dmg_settings.py"
    jhbuild run dmgbuild -s "$DMG_SETTINGS" -D app="$QUODLIBET" \
        "Quod Libet $VERSION" "$QL_OSXBUNDLE_BUNDLE_DEST/QuodLibet-$VERSION.dmg"
    jhbuild run dmgbuild -s "$DMG_SETTINGS" -D app="$EXFALSO" \
        "Ex Falso $VERSION" "$QL_OSXBUNDLE_BUNDLE_DEST/ExFalso-$VERSION.dmg"

    (cd "$QL_OSXBUNDLE_BUNDLE_DEST" && \
        shasum -a256 "QuodLibet-$VERSION.dmg" > "QuodLibet-$VERSION.dmg.sha256")
    (cd "$QL_OSXBUNDLE_BUNDLE_DEST" && \
        shasum -a256 "ExFalso-$VERSION.dmg" > "ExFalso-$VERSION.dmg.sha256")
}

main "$@";
