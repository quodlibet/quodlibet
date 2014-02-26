#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"

if [ ! -d "$DIR"/_sdk ]; then
    "$DIR"/build_sdk.sh
fi

"$DIR"/_sdk/test.sh
