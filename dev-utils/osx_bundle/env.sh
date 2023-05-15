#!/usr/bin/env bash
shopt -s expand_aliases

DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$DIR" || exit

ORIG_HOME="$HOME"
export HOME="$DIR/_home"
export QL_OSXBUNDLE_JHBUILD_DEST="$DIR/_jhbuild"
export QL_OSXBUNDLE_BUNDLER_DEST="$DIR/_bundler"
export QL_OSXBUNDLE_BUNDLE_DEST="$DIR/_build"

export CARGO_HOME="$ORIG_HOME/.cargo"
export RUSTUP_HOME="$ORIG_HOME/.rustup"

export PATH="$PATH:$HOME/.local/bin"
export QL_OSXBUNDLE_MODULESETS_DIR="$DIR/modulesets"
# shellcheck disable=SC2139
alias jhbuild="python2.7 $(which jhbuild)"
