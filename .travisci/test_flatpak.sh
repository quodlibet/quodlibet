#!/bin/bash

set -e

DIR="$( cd "$( dirname "$0" )" && pwd )"

if [[ $1 == "inflatpak" ]]; then
    cd quodlibet
    python3 -m pip install --user pytest pyflakes pycodestyle
    python3 setup.py test
else
    sudo add-apt-repository --yes ppa:alexlarsson/flatpak
    sudo apt-get update
    sudo apt-get install -y ca-certificates flatpak xvfb

    flatpak remote-add --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    flatpak remote-add --user gnome-nightly https://sdk.gnome.org/gnome-nightly.flatpakrepo
    flatpak install --user -y flathub io.github.quodlibet.QuodLibet
    xvfb-run -a flatpak run --user --command="bash" io.github.quodlibet.QuodLibet "${DIR}"/test_flatpak.sh inflatpak
fi
