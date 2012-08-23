# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Niklas Janlert 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

extensions = [".tta"]

try:
    from mutagen.trueaudio import TrueAudio
except ImportError:
    TrueAudio = None
    extensions = []
from quodlibet.formats._id3 import ID3File

class TrueAudioFile(ID3File):
    format = "True Audio"
    mimes = ["audio/x-tta"]
    Kind = TrueAudio

info = TrueAudioFile
types = [TrueAudioFile]
