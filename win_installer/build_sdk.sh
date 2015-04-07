#!/bin/bash
# Copyright 2013, 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

DIR="$( cd "$( dirname "$0" )" && pwd )"

source "$DIR"/_base.sh

download_and_verify;

init_wine;
init_build_env;
extract_deps;

setup_deps;
install_python;
install_pydeps;
install_git;

cleanup;
setup_sdk;
