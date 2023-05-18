#!/bin/bash

set -e

sudo apt-get update -qq
sudo apt-get install -qq -y ca-certificates flatpak xvfb libsoup-3.0-0

flatpak remote-add --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user -y flathub io.github.quodlibet.QuodLibet
flatpak install --user -y "$(flatpak info io.github.quodlibet.QuodLibet --show-sdk)"
