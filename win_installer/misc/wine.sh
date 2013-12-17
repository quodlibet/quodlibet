#!/bin/sh

DIR="$( cd "$( dirname "$0" )" && pwd )"
export WINEPREFIX="$DIR"/_wine_prefix
export WINEDEBUG=-all
export WINEARCH=win32
wine cmd
