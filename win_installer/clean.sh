#!/bin/bash
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

DIR="$( cd "$( dirname "$0" )" && pwd )"

rm -f "$DIR"/_sdk
rm -rf "$DIR"/_build_env
rm -rf "$DIR"/_build_env_installer
rm -f "$DIR"/quodlibet-*.exe
rm -f "$DIR"/quodlibet-win-sdk.tar.gz
