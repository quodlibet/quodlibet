#!/bin/bash

shopt -s expand_aliases

DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$DIR"

export HOME="$DIR/_home"
export QL_OSXBUNDLE_JHBUILD_DEST="$DIR/_jhbuild"
export QL_OSXBUNDLE_BUNDLER_DEST="$DIR/_bundler"
export QL_OSXBUNDLE_BUNDLE_DEST="$DIR/_build"

export PATH="$PATH:$HOME/.local/bin"
export QL_OSXBUNDLE_MODULESETS_DIR="$DIR/modulesets"
alias jhbuild="python2.7 `which jhbuild`"
