#!/bin/bash

set -e
DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "${DIR}"

rm -Rf appcast
./make.py

rm -Rf _temp
git clone https://github.com/quodlibet/quodlibet.github.io.git _temp
cp appcast/* _temp/appcast
cd _temp
git add appcast
git commit -m "update appcast" || true
git push
cd ..
rm -Rf _temp
rm -Rf appcast
