#!/bin/bash

set -e

for name in quodlibet exfalso; do
    convert ../../quodlibet/quodlibet/images/hicolor/*/apps/${name}.png "${name}.ico"
done
