#!/bin/bash

set -e

RUN="$TMPDIR/_app/Contents/MacOS/run"
$RUN -R -bb setup.py test
