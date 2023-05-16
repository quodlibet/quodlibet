#!/usr/bin/env bash
# We use lots of embedded quotes here that worry Shellcheck, so disable rule
# shellcheck disable=SC2016

set -e

usage() {
    echo "FATAL: $*"
    echo "Usage: $(basename "$0") SINCE_RELEASE"
    exit 1
}
GIT_REGEX='^.* #([0-9]+) from ([^/]+)\/.+\|(.*)$'
last_release=$1
test -z "$last_release" && usage "need a release version"
from_date=$(git log -1 --format=%ai "release-$last_release")
echo "From '$from_date'" >/dev/stderr

git log \
    --pretty=format:"%s|%b" \
    --merges \
    --since="$from_date" \
    --grep "pull request" \
    | sed -nre "s/$GIT_REGEX"'/ * \3 :pr:`\1` (:user:`\2`)/p'
echo -e "\n\nMaster:"
git log \
    --pretty=format:"%aN|%s" \
    --no-merges \
    --invert-grep \
    --grep "pull request" \
    --grep "Update translation files" \
    --grep "Translated using Weblate" \
    --grep "Update quodlibet.pot" \
    --first-parent main \
    --since="$from_date" \
    | sed -nre 's/(.+)+\|(.*)/ * \2 (:user:`\1`)/p' \
    | sed -r \
          -e 's/`Nick B`|`Nick Boultbee`/`Nick Boultbee <declension>`/g' \
          -e 's/`lazka`/`Christoph Reiter <lazka>`/g' \
          -e 's/`Christoph Reiter`|`lazka`/`Christoph Reiter <lazka>`/g' \
          -e 's/`Joschua Gandert`/`Joschua Gandert <CreamyCookie>`/g'
echo
