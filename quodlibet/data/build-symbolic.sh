#!/bin/bash

# This script takes foo-symbolic-svg.in files, converts the strokes to paths,
# adds all the paths together and copies the result into our hicolor theme
# without the .in extension.
# Note that this will remove all object fills..

set -e

DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$DIR"

function build_symbolic {
    echo "Build $1"
    cp "$1.in" "temp-$1"
    inkscape -f "temp-$1" --verb=EditSelectAll \
        --verb=SelectionUnGroup --verb=StrokeToPath --verb=SelectionUnion \
        --verb=FileVacuum \
        --verb=FileSave --verb=FileClose --verb=FileQuit
    mv "temp-$1" "../quodlibet/images/hicolor/scalable/apps/$1"
    echo "done"
}

build_symbolic "exfalso-symbolic.svg"
build_symbolic "quodlibet-symbolic.svg"
echo "all done"
