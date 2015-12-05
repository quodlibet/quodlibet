#!/bin/bash

trap 'exit 1' SIGINT;

DIR="$( cd "$( dirname "$0" )" && pwd )"
export WINEPREFIX="$DIR"/_wine_prefix
export WINEDEBUG=-all
export WINEARCH=win32
export WINEDLLOVERRIDES="mscoree,mshtml="

SETUP=$(readlink -f $1)
shift
OTHERS=$*
(cd "$DIR" && wine cmd /c env.bat python $(wine winepath -w $SETUP) $OTHERS)
exit $?
