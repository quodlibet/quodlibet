#! /usr/bin/env python
# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# This is a total hack originally designed to make it easier to test some
# backend mods. It coexists with a running QL.
# Usage: python qlay.py <backend> <files...>
#  e.g.: python qlay.py oss 01.mp3 02.ogg

import sys
import const
import config
config.init(const.CONFIG)

class sink(object):
    def __getattr__(self, attr): return self
    def __call__(self, *args, **kwargs): return self

import library
import __builtin__
__builtin__._ = str

library.init()
from library import library
for fn in sys.argv[2:]:
    library.add(fn)

import player
player.init(sys.argv[1])
player.playlist.filter = lambda s: True
player.playlist.refilter()
from threading import Thread
t = Thread(target=player.playlist.play, args=(sink(),))
t.start()
import time
try:
    for fn in sys.argv[2:]:
        song = library[fn]
        player.playlist.go_to(song)
        player.playlist.paused = False
        while not player.playlist.paused:
            time.sleep(1)
finally:
    player.playlist.quitting()
    t.join()
