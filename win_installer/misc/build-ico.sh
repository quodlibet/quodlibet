#!/bin/bash

set -e

for name in quodlibet exfalso; do
    path="../../quodlibet/quodlibet/images/hicolor/256x256/apps/${name}.png"
    convert -background transparent \
        "${path}" \
        -define icon:auto-resize=16,32,48,256 \
        "${name}.ico"
done
