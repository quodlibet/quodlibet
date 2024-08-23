#!/usr/bin/env bash
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

DIR="$( cd "$( dirname "$0" )" && pwd )"
# shellcheck source-path=SCRIPTDIR
source "$DIR"/_base.sh

set_build_root "${DIR}/_rebuild_root"

function main {
    local INSTALLER_PATH=${1}
    local GIT_TAG=${2:-"main"}

    [[ -d "${BUILD_ROOT}" ]] && (echo "${BUILD_ROOT} already exists"; exit 1)

    install_pre_deps
    create_root
    extract_installer "$INSTALLER_PATH"
    cleanup_before
    install_quodlibet "$GIT_TAG"
    cleanup_after
    build_installer
    build_portable_installer
}

main "$@";
