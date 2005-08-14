# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import audioop
from formats.audio import AudioFile, AudioPlayer

try: import ogg.vorbis
except ImportError: extensions = []
else: extensions = [".ogg"]

class OggFile(AudioFile):
    def __init__(self, filename):
        import ogg.vorbis
        f = ogg.vorbis.VorbisFile(filename)
        for k, v in f.comment().as_dict().iteritems():
            if not isinstance(v, list): v = [v]
            v = u"\n".join(map(unicode, v))
            self[k.lower()] = v

        self["~#length"] = int(f.time_total(-1))
        self["~#bitrate"] = int(f.bitrate(-1))

        try: del(self["vendor"])
        except KeyError: pass

        if "totaltracks" in self:
            self["tracktotal"].setdefault(self["totaltracks"])
            del(self["totaltracks"])

        # tracktotal is incredibly stupid; use tracknumber=x/y instead.
        if "tracktotal" in self:
            if "tracknumber" in self:
                self["tracknumber"] += "/" + self["tracktotal"]
            del(self["tracktotal"])

        self.sanitize(filename)

    def can_change(self, k=None):
        if k is None: return AudioFile.can_change(self, None)
        else: return (AudioFile.can_change(self, k) and
                      k not in ["vendor", "totaltracks", "tracktotal"])

    def write(self):
        import ogg.vorbis
        f = ogg.vorbis.VorbisFile(self['~filename'])
        comments = f.comment()
        comments.clear()
        for key in self.realkeys():
            value = self.list(key)
            for line in value: comments[key] = line
        comments.write_to(self['~filename'])
        self.sanitize()

class OggPlayer(AudioPlayer):
    def __init__(self, dev, song):
        AudioPlayer.__init__(self)
        filename = song['~filename']
        import ogg.vorbis
        self.error = ogg.vorbis.VorbisError
        self.dev = dev
        self.audio = ogg.vorbis.VorbisFile(filename)
        rate = self.audio.info().rate
        channels = self.audio.info().channels
        self.dev.set_info(rate, channels)
        self.length = int(self.audio.time_total(-1) * 1000)
        self.replay_gain(song)

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.time_seek(ms / 1000.0)

    def next(self):
        if self.stopped: raise StopIteration
        try: (buff, bytes, bit) = self.audio.read(256)
        except self.error: pass
        else:
            if bytes == 0: raise StopIteration
            if self.scale != 1:
                buff = audioop.mul(buff, 2, self.scale)
            self.dev.play(buff)
        return int(self.audio.time_tell() * 1000)

info = OggFile
player = OggPlayer
