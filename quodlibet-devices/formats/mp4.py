# Copyright 2005 Alexey Bobyakov <claymore.ws@gmail.com>, Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Based on quodlibet/formats/mpc.py by Joe Wreschnig, Michael Urman

import tempfile

import gst

from formats._audio import AudioFile

extensions = ['.mp4', '.m4a']
try:
    import ctypes
    _mp4v2 = ctypes.cdll.LoadLibrary("libmp4v2.so.0")
except (ImportError, OSError):
    extensions = []
else:
    _mp4v2.MP4Read.restype = ctypes.c_void_p
    _mp4v2.MP4GetTrackType.restype = ctypes.c_char_p
    _mp4v2.MP4GetTrackDuration.restype = ctypes.c_uint64
    _mp4v2.MP4ConvertFromTrackDuration.restype = ctypes.c_uint64
    _mp4v2.MP4FindTrackId.restype = ctypes.c_uint32
    _mp4v2.MP4GetNumberOfTracks.restype = ctypes.c_uint32

    if gst.registry_get_default().find_plugin("faad") is None:
        extensions = []

def GetAACTrack(infile):
    numtracks = _mp4v2.MP4GetNumberOfTracks(infile, None, ctypes.c_uint8(0))
    for i in range(numtracks):
        trackid = _mp4v2.MP4FindTrackId(
            infile, ctypes.c_uint16(i), None, ctypes.c_uint8(0))
        tracktype = _mp4v2.MP4GetTrackType(infile, ctypes.c_uint32(trackid))
        if tracktype == "soun": return trackid
    else: return -1

class MP4File(AudioFile):
    multiple_values = False
    format = "MPEG-4 AAC"

    def __init__(self, filename):
        try:
            f = _mp4v2.MP4Read(filename, ctypes.c_uint32(0))
            if not f: raise IOError("%s not an MP4 file" % filename)
            track = GetAACTrack(f)
            if track == -1: raise IOError("%s has no audio track")
            duration = _mp4v2.MP4GetTrackDuration(f, ctypes.c_uint32(track))
            length = _mp4v2.MP4ConvertFromTrackDuration(
                f, ctypes.c_uint32(track), ctypes.c_uint64(duration),
                ctypes.c_uint32(1))
            self["~#length"] = int(length)

            self.__fill_metadata(f)
            self.sanitize(filename)
        finally:
            _mp4v2.MP4Close(f)

    def __fill_metadata(self, f):
        from ctypes import byref
        for key, function in [
            ("title", _mp4v2.MP4GetMetadataName),
            ("artist", _mp4v2.MP4GetMetadataArtist),
            ("composer", _mp4v2.MP4GetMetadataWriter),
            ("comment", _mp4v2.MP4GetMetadataComment),
            ("date", _mp4v2.MP4GetMetadataYear),
            ("album", _mp4v2.MP4GetMetadataAlbum),
            ("encoder", _mp4v2.MP4GetMetadataTool),
            ("genre", _mp4v2.MP4GetMetadataGenre)]:
            value = ctypes.c_char_p()
            if function(f, byref(value)):
                self[key] = value.value.decode('utf-8')

        cur, total = ctypes.c_uint16(), ctypes.c_uint16()
        if _mp4v2.MP4GetMetadataTrack(f, byref(cur), byref(total)):
            if total.value:
                self["tracknumber"] = "%d/%d" % (cur.value, total.value)
            else:
                self["tracknumber"] = "%d" % cur.value
        if _mp4v2.MP4GetMetadataDisk(f, byref(cur), byref(total)):
            if total.value:
                self["discnumber"] = "%d/%d" % (cur.value, total.value)
            else:
                self["discnumber"] = "%d" % cur.value

    def write(self):
        try:
            filename = self["~filename"]
            f = _mp4v2.MP4Modify(
                filename, ctypes.c_uint32(0), ctypes.c_uint32(0))
            if not f: raise IOError("%s not an MP4 file" % filename)
            elif not _mp4v2.MP4MetadataDelete(f):
                raise IOError("unable to remove metadata in %s" % filename)
            for key, func in [
                ("title", _mp4v2.MP4SetMetadataName),
                ("artist", _mp4v2.MP4SetMetadataArtist),
                ("composer", _mp4v2.MP4SetMetadataWriter),
                ("comment", _mp4v2.MP4SetMetadataComment),
                ("date", _mp4v2.MP4SetMetadataYear),
                ("album", _mp4v2.MP4SetMetadataAlbum),
                ("encoder", _mp4v2.MP4SetMetadataTool),
                ("genre", _mp4v2.MP4SetMetadataGenre)]:
                if key in self and not func(f, self[key].encode("utf-8")):
                    raise IOError("unable to set %s in %s" % (key, filename))

            track, tracks = self("~#track"), self("~#tracks", 0)
            if track:
                if not _mp4v2.MP4SetMetadataTrack(
                    f, ctypes.c_uint16(track), ctypes.c_uint16(tracks)):
                    raise IOError("unable to set track in %s" % filename)

            disc, discs = self("~#disc"), self("~#discs", 0)
            if disc:
                if not _mp4v2.MP4SetMetadataDisk(
                    f, ctypes.c_uint16(disc), ctypes.c_uint16(discs)):
                    raise IOError("unable to set track in %s" % filename)

        finally:
            _mp4v2.MP4Close(f)
            self.sanitize()

    def can_change(self, key=None):
        OK = ["title", "artist", "composer", "comment", "date", "encoder",
              "genre", "tracknumber", "discnumber", "album"]
        if key is None: return super(MP4File, self).can_change(key) and OK
        else: return super(MP4File, self).can_change(key) and (key in OK)

    def get_format_cover(self):
        try:
            from ctypes import byref
            value = ctypes.c_char_p()
            size = ctypes.c_uint32()
            f = _mp4v2.MP4Read(self["~filename"], ctypes.c_uint32(0))
            if _mp4v2.MP4GetMetadataCoverArt(f, byref(value), byref(size)):
                fn = tempfile.NamedTemporaryFile()
                fn.write(value.value)
                fn.flush()
                fn.seek(0, 0)
                return fn
        finally:
            _mp4v2.MP4Close(f)

info = MP4File
