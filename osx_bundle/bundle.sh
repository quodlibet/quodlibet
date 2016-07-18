#!/bin/bash

# pass the tag/revision to install, or install the current revision
# if nothing is passed

set -e

source env.sh

jhbuild run gtk-mac-bundler misc/bundle/app.bundle

APP="$QL_OSXBUNDLE_BUNDLE_DEST/Application.app"
APP_PREFIX="$APP"/Contents/Resources
DMG_SETTINGS="misc/dmg_settings.py"

# clone this repo and install into the bundle
CLONE="$QL_OSXBUNDLE_BUNDLE_DEST"/_temp_clone
git clone ../ "$CLONE"
if [ $# -eq 1 ]; then
    (cd "$CLONE"; git checkout "$1";)
fi
jhbuild run "$CLONE"/quodlibet/setup.py install --prefix="$APP_PREFIX" --record="$QL_OSXBUNDLE_BUNDLE_DEST"/_install_log.txt
rm -Rf "$CLONE"

# kill some useless files
rm -f "$APP_PREFIX"/lib/python2.7/site-packages/*.egg-info
rm -f "$APP_PREFIX"/lib/python2.7/config/libpython2.7.a
rm -Rf "$APP_PREFIX"/lib/python2.7/*/test
rm -f "$APP"/Contents/MacOS/_launcher-bin
rm -Rf "$APP_PREFIX"/include/
./misc/prune_translations.py "$APP_PREFIX"/share/locale

# only keep *.pyc
find "$APP_PREFIX"/lib/python2.7 -name '*.pyo' -delete

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

echo 'BUILD_TYPE = u"osx-exfalso"' >> "$EXFALSO_PREFIX"/lib/python2.7/site-packages/quodlibet/build.py
echo 'BUILD_TYPE = u"osx-quodlibet"' >> "$QUODLIBET_PREFIX"/lib/python2.7/site-packages/quodlibet/build.py

jhbuild run python -m compileall -f "$EXFALSO_PREFIX"/lib/python2.7
jhbuild run python -m compileall -f "$QUODLIBET_PREFIX"/lib/python2.7
find "$EXFALSO_PREFIX"/lib/python2.7 -name '*.py' -delete
find "$QUODLIBET_PREFIX"/lib/python2.7 -name '*.py' -delete

VERSION=$("$QUODLIBET"/Contents/MacOS/run -c "import sys;import quodlibet.const;sys.stdout.write(quodlibet.const.VERSION)")
./misc/fixup_info.py "$QUODLIBET"/Contents/Info.plist "quodlibet" "Quod Libet" "$VERSION"
./misc/fixup_info.py "$EXFALSO"/Contents/Info.plist "exfalso" "Ex Falso" "$VERSION"

./misc/list_content.py "$HOME/jhbuild_prefix" "$QUODLIBET" > "$QUODLIBET/Contents/Resources/content.txt"
./misc/list_content.py "$HOME/jhbuild_prefix" "$EXFALSO" > "$EXFALSO/Contents/Resources/content.txt"

jhbuild run dmgbuild -s "$DMG_SETTINGS" -D app="$QUODLIBET" "Quod Libet $VERSION" "$QL_OSXBUNDLE_BUNDLE_DEST/QuodLibet-$VERSION.dmg"
jhbuild run dmgbuild -s "$DMG_SETTINGS" -D app="$EXFALSO" "Ex Falso $VERSION" "$QL_OSXBUNDLE_BUNDLE_DEST/ExFalso-$VERSION.dmg"

(cd "$QL_OSXBUNDLE_BUNDLE_DEST" && shasum -a256 "QuodLibet-$VERSION.dmg" > "QuodLibet-$VERSION.dmg.sha256")
(cd "$QL_OSXBUNDLE_BUNDLE_DEST" && shasum -a256 "ExFalso-$VERSION.dmg" > "ExFalso-$VERSION.dmg.sha256")
