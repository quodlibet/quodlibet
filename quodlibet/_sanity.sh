#!/bin/sh

echo "Proceding to doubt the sanity of the developers."

make test

grep "except None:" *.py */*.py
./quodlibet.py --help > /dev/null
./quodlibet.py --version > /dev/null
