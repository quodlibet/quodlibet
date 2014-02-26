#!/bin/bash
# Copyright 2013, 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

DIR="$( cd "$( dirname "$0" )" && pwd )"

source "$DIR"/_base.sh

build_all;

setup_sdk;
