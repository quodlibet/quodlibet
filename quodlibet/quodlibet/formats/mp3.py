# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Niklas Janlert 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from mutagen.mp3 import MP3
from quodlibet import player
from quodlibet.formats._id3 import ID3File

extensions = [".mp3", ".mp2"]
if not player.can_play_mime("audio/mpeg"):
    extensions = []

class MP3File(ID3File):
    format = "MP3"
    Kind = MP3

info = MP3File
