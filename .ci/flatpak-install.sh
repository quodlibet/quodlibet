#!/bin/bash

set -e

sudo add-apt-repository --yes ppa:alexlarsson/flatpak
sudo apt-get update
sudo apt-get install -y ca-certificates flatpak xvfb

flatpak remote-add --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user -y flathub io.github.quodlibet.QuodLibet
flatpak install --user -y "$(flatpak info io.github.quodlibet.QuodLibet --show-sdk)"