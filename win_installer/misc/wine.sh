#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"
export WINEPREFIX="$DIR"/_wine_prefix
export WINEDEBUG=-all
export WINEARCH=win32
DISPLAY=be_quiet_damnit wine wineboot -u
wine cmd /k env.bat
