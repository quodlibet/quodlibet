#! /usr/bin/env python
# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# This is a total hack originally designed to make it easier to test some
# backend mods. It coexists with a running QL.
# Usage: python qlay.py <backend> <files...>
#  e.g.: python qlay.py oss 01.mp3 02.ogg

import sys
import const
import config
import formats
config.init(const.CONFIG)

class sink(object):
    def __getattr__(self, attr): return self
    def __call__(self, *args, **kwargs): return self

import __builtin__
__builtin__._ = str

import player
player.init(sys.argv[1])
from threading import Thread
t = Thread(target=player.playlist.play, args=(sink(), None))
t.start()
import time
try:
    songs = map(formats.MusicFile, sys.argv[1:])
    player.playlist.set_playlist(songs)
    player.playlist.paused = False
    while not player.playlist.paused: time.sleep(1)
finally:
    player.playlist.quitting()
    t.join()
