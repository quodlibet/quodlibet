# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, stat, audioop
from formats.audio import AudioFile, AudioPlayer
import util

try: import flac.metadata, flac.decoder
except: extensions = []
else: extensions = [".flac"]

class FLACFile(AudioFile):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise IOError("%s does not exist" % filename)
        chain = flac.metadata.Chain()
        chain.read(filename)
        it = flac.metadata.Iterator()
        it.init(chain)
        vc = None
        while True:
            if it.get_block_type() == flac.metadata.VORBIS_COMMENT:
                block = it.get_block()
                vc = flac.metadata.VorbisComment(block)
            elif it.get_block_type() == flac.metadata.STREAMINFO:
                info = it.get_block().data.stream_info
                self["~#length"] = (info.total_samples // info.sample_rate)
            if not it.next(): break

        if vc:
            for k in vc.comments:
                parts = k.split("=")
                key = parts[0].lower()
                val = util.decode("=".join(parts[1:]))
                if key in self: self[key] += "\n" + val
                else: self[key] = val
        self.sanitize(filename)

    def write(self):
        chain = flac.metadata.Chain()
        chain.read(self['~filename'])
        it = flac.metadata.Iterator()
        it.init(chain)
        vc = None
        while True:
            if it.get_block_type() == flac.metadata.VORBIS_COMMENT:
                block = it.get_block()
                vc = flac.metadata.VorbisComment(block)
                break
            if not it.next(): break

        if vc:
            keys = [k.split("=")[0] for k in vc.comments]
            for k in keys: del(vc.comments[k])
            for key in self.realkeys():
                value = self.list(key)
                for line in value:
                    vc.comments[key] = util.encode(line)
            chain.write(True, True)

class FLACPlayer(AudioPlayer):
    def __init__(self, dev, song):
        AudioPlayer.__init__(self)
        filename = song['~filename']
        if not os.path.exists(filename):
            raise IOError("%s does not exist" % filename)
        self.STREAMINFO = flac.metadata.STREAMINFO
        self.EOF = flac.decoder.FLAC__FILE_DECODER_END_OF_FILE
        self.OK = flac.decoder.FLAC__FILE_DECODER_OK
        self.dev = dev
        self.dec = flac.decoder.FileDecoder()
        self.dec.set_md5_checking(False);
        self.dec.set_filename(filename)
        self.dec.set_metadata_respond_all()
        self.dec.set_write_callback(self._player)
        self.dec.set_metadata_callback(self._grab_stream_info)
        self.dec.set_error_callback(lambda *args: None)
        self.dec.init()
        self.dec.process_until_end_of_metadata()
        self.pos = 0
        self._size = os.stat(filename)[stat.ST_SIZE]
        self.replay_gain(song)

    def _grab_stream_info(self, dec, block):
        if block.type == self.STREAMINFO:
            streaminfo = block.data.stream_info
            self._srate = streaminfo.sample_rate
            self._bps = streaminfo.bits_per_sample // 8
            self._chan = streaminfo.channels
            self._samples = streaminfo.total_samples
            self.length = (self._samples * 1000) // self._srate
        return self.OK

    def _player(self, dec, buff, size):
        self.pos += 1000 * (float(len(buff))/self._chan/self._bps/self._srate)
        if self.scale != 1:
            buff = audioop.mul(buff, self._chan, self.scale)
        self.dev.set_info(self.dec.get_sample_rate(), self.dec.get_channels())
        self.dev.play(buff)
        return self.OK

    def next(self):
        if self.stopped:
            self.dec.finish()
            raise StopIteration
        if self.dec.get_state() == self.EOF:
            self.dec.finish()
            raise StopIteration
        if not self.dec.process_single():
            self.dec.finish()
            raise StopIteration
        return int(self.pos)

    def __iter__(self):
        return self

    def seek(self, ms):
        self.pos = ms
        sample = (ms / 1000.0) * self._srate
        self.dec.seek_absolute(long(sample))

info = FLACFile
player = FLACPlayer
