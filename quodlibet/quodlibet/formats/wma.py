# Copyright 2006 Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import struct

from quodlibet.util.path import get_temp_cover_file
from quodlibet.formats._audio import AudioFile
from quodlibet.formats._image import EmbeddedImage, APICType

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
                self.has_images = True
            try:
                name = self.__translate[name]
            except KeyError:
                continue
            self[name] = "\n".join(map(unicode, values))
        self.sanitize(filename)

    def write(self):
        audio = mutagen.asf.ASF(self["~filename"])
        for key in self.__translate.keys():
            try:
                del(audio[key])
            except KeyError:
                pass

        for key in self.realkeys():
            try:
                name = self.__rtranslate[key]
            except KeyError:
                continue
            audio.tags[name] = self.list(key)
        audio.save()
        self.sanitize()

    def can_change(self, key=None):
        OK = self.__rtranslate.keys()
        if key is None:
            return OK
        else:
            return super(WMAFile, self).can_change(key) and (key in OK)

    def get_primary_image(self):
        """Returns the primary embedded image or None"""

        try:
            tag = mutagen.asf.ASF(self["~filename"])
        except Exception:
            return

        for image in tag.get("WM/Picture", []):
            try:
                (mime, desc, data, type_) = unpack_image(image.value)
            except ValueError:
                continue
            if type_ == APICType.COVER_FRONT:  # Only cover images
                f = get_temp_cover_file(data)
                return EmbeddedImage(mime, -1, -1, -1, f)

    can_change_images = True

    def clear_images(self):
        """Delete all embedded images"""

        try:
            tag = mutagen.asf.ASF(self["~filename"])
        except Exception:
            return

        tag.pop("WM/Picture", None)
        tag.save()

        self.has_images = False

    def set_image(self, image):
        """Replaces all embedded images by the passed image"""

        try:
            tag = mutagen.asf.ASF(self["~filename"])
        except Exception:
            return

        try:
            imagedata = image.file.read()
        except EnvironmentError:
            return

        # thumbnail gets used in WMP..
        data = pack_image(image.mime_type, u"thumbnail",
                          imagedata, APICType.COVER_FRONT)

        value = mutagen.asf.ASFValue(data, mutagen.asf.BYTEARRAY)
        tag["WM/Picture"] = [value]
        tag.save()

        self.has_images = True


def unpack_image(data):
    """
    Helper function to unpack image data from a WM/Picture tag.

    The data has the following format:
    1 byte: Picture type (0-20), see ID3 APIC frame specification at
    http://www.id3.org/id3v2.4.0-frames
    4 bytes: Picture data length in LE format
    MIME type, null terminated UTF-16-LE string
    Description, null terminated UTF-16-LE string
    The image data in the given length
    """

    try:
        (type_, size) = struct.unpack_from("<bi", data)
    except struct.error as e:
        raise ValueError(e)
    data = data[5:]

    mime = ""
    while data:
        char, data = data[:2], data[2:]
        if char == "\x00\x00":
            break
        mime += char
    else:
        raise ValueError("mime: missing data")

    mime = mime.decode("utf-16-le")

    description = ""
    while data:
        char, data = data[:2], data[2:]
        if char == "\x00\x00":
            break
        description += char
    else:
        raise ValueError("desc: missing data")

    description = description.decode("utf-16-le")

    if size != len(data):
        raise ValueError("image data size mismatch")

    return (mime, description, data, type_)


def pack_image(mime, description, imagedata, type_):
    assert APICType.is_valid(type_)

    size = len(imagedata)
    data = struct.pack("<bi", type_, size)
    data += mime.encode("utf-16-le") + "\x00\x00"
    data += description.encode("utf-16-le") + "\x00\x00"
    data += imagedata

    return data


info = WMAFile
types = [WMAFile]
