#!/bin/bash

set -e

sudo add-apt-repository --yes ppa:alexlarsson/flatpak
sudo apt-get update
sudo apt-get install -y ca-certificates flatpak xvfb python3-pip

flatpak remote-add --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak remote-add --user gnome-nightly https://nightly.gnome.org/gnome-nightly.flatpakrepo
flatpak install --user -y flathub io.github.quodlibet.QuodLibet
