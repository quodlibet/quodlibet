# Copyright 2005 Alexey Bobyakov <claymore.ws@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Based on quodlibet/formats/mpc.py by Joe Wreschnig, Michael Urman

import gst
import tempfile
from formats._audio import AudioFile

try: import mp4info
except ImportError: extensions = []
else:
    if gst.element_factory_make("faad"):
        extensions = ['.mp4', '.m4a']
    else: extensions = []

class MP4File(AudioFile):
    TRANS = { "\251nam": "title",
              "\251ART": "artist",
              "\251wri": "lyricist",
              "\251alb": "album",
              "\251too": "encoder",
              "\251wrt": "composer",
              "\251cmt": "comment",
              "\251gen": "genre",
              "\251grp": "grouping",
              "\251day": "date",
              "disk": "discnumber",
              "trkn": "tracknumber",
              "tmpo": "bpm",
              "cpil": "compilation"
            }
    SNART = dict([(v, k) for k, v in TRANS.iteritems()])
    BINARY = [mp4info.itunes.COVER, mp4info.itunes.FREE_FORM_BINARY]
    
    def __init__(self, filename):
        tag = mp4info.iTunesTag(filename)
        for key, value in tag:
            if key == "gnre":
                key = "genre"
                self[key] = tag.genre_to_string(str(value))
            elif value.kind not in MP4File.BINARY:
                key = MP4File.TRANS.get(key, key)
                self[key] = "\n".join(list(value))
        f = mp4info.MP4File(filename)
        self["~#length"] = f.length // 1000
        try: self["~#bitrate"] = int(f.bitrate)
        except AttributeError: pass
        self.sanitize(filename)
        
    def can_change(self, key = None):
        if key is None: return True
        else: return AudioFile.can_change(self, key)

    def write(self):
        tag = mp4info.iTunesTag(self["~filename"])
        keys = tag.keys()
        for key in keys:
            # remove any text keys we read in
            value = tag[key]
            if value.kind not in MP4File.BINARY:
                del(tag[key])
        for key in self.realkeys():
            value = self[key]
            key = MP4File.SNART.get(key, key)
            tag[key] = value.split("\n")
        tag.write()
        self.sanitize()
    
    def get_format_cover(self):
        f = tempfile.NamedTemporaryFile()
        tag = mp4info.iTunesTag(self["~filename"])
        if (tag.contains("covr")):
            f.write(tag["covr"])
            f.flush()
            f.seek(0, 0)
            return f
        else:
            f.close()
            return None

info = MP4File
