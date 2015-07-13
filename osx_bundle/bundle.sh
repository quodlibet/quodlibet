#!/bin/sh

source env.sh

jhbuild run gtk-mac-bundler misc/bundle/app.bundle

APP="$QL_OSXBUNDLE_BUNDLE_DEST/Application.app"
rm -f "$APP"/Contents/Resources/lib/python2.7/config/libpython2.7.a
rm -f "$APP"/Contents/MacOS/_launcher-bin
rm -Rf "$APP"/Contents/Resources/include/
./misc/prune_translations.py "$APP"/Contents/Resources/share/locale

(cd "$APP"/Contents/MacOS/ && ln -s _launcher quodlibet)
(cd "$APP"/Contents/MacOS/ && ln -s _launcher exfalso)
(cd "$APP"/Contents/MacOS/ && ln -s _launcher operon)
(cd "$APP"/Contents/MacOS/ && ln -s _launcher run)

VERSION=$(jhbuild run python -c "import sys;import quodlibet.const;sys.stdout.write(quodlibet.const.VERSION)")
EXFALSO="$QL_OSXBUNDLE_BUNDLE_DEST/ExFalso.app"
QUODLIBET="$QL_OSXBUNDLE_BUNDLE_DEST/QuodLibet.app"

cp -R "$APP" "$EXFALSO"
mv "$APP" "$QUODLIBET"

./misc/fixup_info.py "$QUODLIBET"/Contents/Info.plist "quodlibet" "Quod Libet" "$VERSION"
./misc/fixup_info.py "$EXFALSO"/Contents/Info.plist "exfalso" "Ex Falso" "$VERSION"

(cd "$QL_OSXBUNDLE_BUNDLE_DEST" && zip -rq "QuodLibet-$VERSION.zip" "QuodLibet.app")
(cd "$QL_OSXBUNDLE_BUNDLE_DEST" && zip -rq "ExFalso-$VERSION.zip" "ExFalso.app")

(cd "$QL_OSXBUNDLE_BUNDLE_DEST" && shasum -a256 "QuodLibet-$VERSION.zip" > "QuodLibet-$VERSION.zip.sha256")
(cd "$QL_OSXBUNDLE_BUNDLE_DEST" && shasum -a256 "ExFalso-$VERSION.zip" > "ExFalso-$VERSION.zip.sha256")