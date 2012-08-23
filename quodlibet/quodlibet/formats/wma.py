# Copyright 2006 Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import tempfile
import struct

from quodlibet.formats._audio import AudioFile

extensions = [".wma"]
try:
    import mutagen.asf
except ImportError:
    extensions = []

class WMAFile(AudioFile):
    multiple_values = False
    mimes = ["audio/x-ms-wma", "audio/x-ms-wmv", "video/x-ms-asf",
             "audio/x-wma", "video/x-wmv"]
    format = "Windows Media Audio"

    #http://msdn.microsoft.com/en-us/library/dd743066%28VS.85%29.aspx
    #http://msdn.microsoft.com/en-us/library/dd743063%28VS.85%29.aspx
    #http://msdn.microsoft.com/en-us/library/dd743220%28VS.85%29.aspx
    __translate = {
        "WM/AlbumTitle": "album",
        "Title": "title",
        "Author": "artist",
        "WM/AlbumArtist": "albumartist",
        "WM/Composer": "composer",
        "WM/Writer": "lyricist",
        "WM/Conductor": "conductor",
        "WM/ModifiedBy": "remixer",
        "WM/Producer": "producer",
        "WM/ContentGroupDescription": "grouping",
        "WM/SubTitle": "discsubtitle",
        "WM/TrackNumber": "tracknumber",
        "WM/PartOfSet": "discnumber",
        "WM/BeatsPerMinute": "bpm",
        "Copyright": "copyright",
        "WM/ISRC": "isrc",
        "WM/Mood": "mood",
        "WM/EncodedBy": "encodedby",
        "MusicBrainz/Track Id": "musicbrainz_trackid",
        "MusicBrainz/Album Id": "musicbrainz_albumid",
        "MusicBrainz/Artist Id": "musicbrainz_artistid",
        "MusicBrainz/Album Artist Id": "musicbrainz_albumartistid",
        "MusicBrainz/TRM Id": "musicbrainz_trmid",
        "MusicIP/PUID": "musicip_puid",
        "WM/Year": "date",
        "WM/OriginalArtist": "originalartist",
        "WM/OriginalAlbumTitle": "originalalbum",
        "WM/AlbumSortOrder": "albumsort",
        "WM/ArtistSortOrder": "artistsort",
        "WM/Genre": "genre",
        "WM/Publisher": "publisher",
        "WM/AuthorURL": "website",
        "Description": "comment"
    }
    __rtranslate = dict([(v, k) for k, v in __translate.iteritems()])

    def __init__(self, filename, audio=None):
        if audio is None:
            audio = mutagen.asf.ASF(filename)
        self["~#length"] = int(audio.info.length)
        self["~#bitrate"] = int(audio.info.bitrate / 1000)
        for name, values in audio.tags.items():
            if name == "WM/Picture":
                self["~picture"] = "y"
            try: name = self.__translate[name]
            except KeyError: continue
            self[name] = "\n".join(map(unicode, values))
        self.sanitize(filename)

    def write(self):
        audio = mutagen.asf.ASF(self["~filename"])
        for key in self.__translate.keys():
            try: del(audio[key])
            except KeyError: pass

        for key in self.realkeys():
            try: name = self.__rtranslate[key]
            except KeyError: continue
            audio.tags[name] = self.list(key)
        audio.save()
        self.sanitize()

    def can_change(self, key=None):
        OK = self.__rtranslate.keys()
        if key is None: return super(WMAFile, self).can_change(key)
        else: return super(WMAFile, self).can_change(key) and (key in OK)

    def get_format_cover(self):
        try:
            tag = mutagen.asf.ASF(self["~filename"])
        except (OSError, IOError):
            return None
        else:
            for image in tag.get("WM/Picture", []):
                (mime, data, type) = unpack_image(image.value)
                if type == 3: # Only cover images
                    fn = tempfile.NamedTemporaryFile()
                    fn.write(data)
                    fn.flush()
                    fn.seek(0, 0)
                    return fn
            else:
                return None

def unpack_image(data):
    """
    Helper function to unpack image data from a WM/Picture tag.

    The data has the following format:
    1 byte: Picture type (0-20), see ID3 APIC frame specification at http://www.id3.org/id3v2.4.0-frames
    4 bytes: Picture data length in LE format
    MIME type, null terminated UTF-16-LE string
    Description, null terminated UTF-16-LE string
    The image data in the given length
    """
    (type, size) = struct.unpack_from("<bi", data)
    pos = 5
    mime = ""
    while data[pos:pos+2] != "\x00\x00":
        mime += data[pos:pos+2]
        pos += 2
    pos += 2
    description = ""
    while data[pos:pos+2] != "\x00\x00":
        description += data[pos:pos+2]
        pos += 2
    pos += 2
    image_data = data[pos:pos+size]
    return (mime.decode("utf-16-le"), image_data, type)

info = WMAFile
types = [WMAFile]
