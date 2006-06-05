# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Niklas Janlert 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import tempfile

import gst

import config
import const

from formats._audio import AudioFile

try:
    import mutagen.id3
    from mutagen.mp3 import MP3
except ImportError:
    extensions = []
else:
    try: gst.element_factory_make("mad")
    except gst.PluginNotFoundError: extensions = []
    else: extensions = [".mp3", ".mp2"]

def isascii(s): return ((len(s) == 0) or (ord(max(s)) < 128))

class ID3hack(mutagen.id3.ID3):
    "Override 'correct' behavior with desired behavior"
    def loaded_frame(self, tag):
        if len(type(tag).__name__) == 3: tag = type(tag).__base__(tag)
        if tag.HashKey in self and tag.FrameID[0] == "T":
            self[tag.HashKey].extend(tag[:])
        else: self[tag.HashKey] = tag

# ID3 is absolutely the worst thing ever.

class MP3File(AudioFile):

    # http://www.unixgods.org/~tilo/ID3/docs/ID3_comparison.html
    # http://www.id3.org/id3v2.4.0-frames.txt
    IDS = { "TIT1": "grouping",
            "TIT2": "title",
            "TIT3": "version",
            "TPE1": "artist",
            "TPE2": "performer", 
            "TPE3": "conductor",
            "TPE4": "arranger",
            "TEXT": "lyricist",
            "TCOM": "composer",
            "TENC": "encodedby",
            "TALB": "album",
            "TRCK": "tracknumber",
            "TPOS": "discnumber",
            "TSRC": "isrc",
            "TCOP": "copyright",
            "TPUB": "organization",
            "TSST": "part",
            "TOLY": "author",
            "TMOO": "mood",
            "TBPM": "bpm",
            "TDRC": "date",
            "TDOR": "originaldate",
            "TOAL": "originalalbum",
            "TOPE": "originalartist",
            "WOAR": "website",
            }
    SDI = dict([(v, k) for k, v in IDS.iteritems()])

    # http://musicbrainz.org/docs/specs/metadata_tags.html
    # http://bugs.musicbrainz.org/ticket/1383
    BRAINZ = {
        u"MusicBrainz Artist Id": "musicbrainz_artistid",
        u"MusicBrainz Album Id": "musicbrainz_albumid",
        u"MusicBrainz Album Artist Id": "musicbrainz_albumartistid",
        u"MusicBrainz TRM Id": "musicbrainz_trmid",
        u"MusicIP PUID": "musicip_puid",
        }
    ZNIARB = dict([(v, k) for k, v in BRAINZ.iteritems()])

    CODECS = ["utf-8"]
    try: CODECS.extend(config.get("editing", "id3encoding").strip().split())
    except: pass # Uninitialized config...
    CODECS.append("iso-8859-1")

    format = "MP3"

    def __init__(self, filename):
        mp3 = MP3(filename, ID3=ID3hack)
        tag = mp3.tags or {}

        for frame in tag.values():
            if frame.FrameID == "APIC" and len(frame.data):
                self["~picture"] = "y"
                continue
            elif frame.FrameID == "TCON":
                self["genre"] = "\n".join(frame.genres)
                continue
            elif frame.FrameID == "TLEN":
                try: self["~#length"] = +frame // 1000
                except ValueError: pass
                continue
            elif (frame.FrameID == "UFID" and
                  frame.owner == "http://musicbrainz.org"):
                self["musicbrainz_trackid"] = frame.data
                continue
            elif frame.FrameID == "POPM":
                count = frame.count
                rating = frame.rating / 255.0
                if frame.email == const.EMAIL:
                    self.setdefault("~#playcount", count)
                    self.setdefault("~#rating", rating)
                elif frame.email == config.get("settings", "save_email"):
                    self["~#playcount"] = count
                    self["~#rating"] = rating
                continue
            elif frame.FrameID == "COMM" and frame.desc == "":
                name = "comment"
            elif frame.FrameID in ["COMM", "TXXX"]:
                if frame.desc.startswith("QuodLibet::"):
                    name = frame.desc[11:]
                elif frame.desc.startswith("replaygain_"):
                    # Some versions of Foobar2000 write broken Replay Gain
                    # tags in this format.
                    name = frame.desc
                elif frame.desc in self.BRAINZ:
                    name = self.BRAINZ[frame.desc]
                else: continue
            elif frame.FrameID == "RVA2":
                self.__process_rg(frame)
                continue
            else: name = self.IDS.get(frame.FrameID, "").lower()

            if not name: continue

            id3id = frame.FrameID
            if id3id.startswith("T"):
                text = "\n".join(map(unicode, frame.text))
            elif id3id == "COMM":
                text = "\n".join(frame.text)
            elif id3id.startswith("W"):
                text = frame.url
                frame.encoding = 0
            else: continue

            if not text: continue
            text = self.__distrust_latin1(text, frame.encoding)
            if text is None: continue

            if name in self: self[name] += "\n" + text
            else: self[name] = text
            self[name] = self[name].strip()

        self.setdefault("~#length", int(mp3.info.length))
        self.setdefault("~#bitrate", int(mp3.info.bitrate))

        self.sanitize(filename)

    def __process_rg(self, frame):
        if frame.channel == 1:            
            if frame.desc == "album": k = "album"
            elif frame.desc == "track": k = "track"
            elif "replaygain_track_gain" not in self: k = "track" # fallback
            else: return
            self["replaygain_%s_gain" % k] = "%+f dB" % frame.gain
            self["replaygain_%s_peak" % k] = str(frame.peak)

    def __distrust_latin1(self, text, encoding):
        assert isinstance(text, unicode)
        if encoding == 0:
            text = text.encode('iso-8859-1')
            for codec in self.CODECS:
                try: text = text.decode(codec)
                except (UnicodeError, LookupError): pass
                else: break
            else: return None
        return text

    def write(self):
        try: tag = mutagen.id3.ID3(self['~filename'])
        except mutagen.id3.error: tag = mutagen.id3.ID3()
        tag.delall("COMM:QuodLibet:")
        tag.delall("TXXX:QuodLibet:")
        for key in ["UFID:http://musicbrainz.org",
                    "POPM:%s" % const.EMAIL,
                    "POPM:%s" % config.get("editing", "save_email")]:
            if key in tag:
                del(tag[key])

        for key, id3name in self.SDI.items():
            tag.delall(id3name)

            if key not in self: continue
            elif not isascii(self[key]): enc = 1
            else: enc = 3

            Kind = mutagen.id3.Frames[id3name]
            text = self[key].split("\n")
            if id3name == "WOAR":
                for t in text:
                    tag.loaded_frame(Kind(url=t))
            else: tag.loaded_frame(Kind(encoding=enc, text=text))

        dontwrite = ["genre", "comment", "replaygain_album_peak",
                     "replaygain_track_peak", "replaygain_album_gain",
                     "replaygain_track_gain", "musicbrainz_trackid",
                     ] + self.BRAINZ.values()

        if "musicbrainz_trackid" in self.realkeys():
            f = mutagen.id3.UFID(owner="http://musicbrainz.org",
                  data=self["musicbrainz_trackid"])
            tag.loaded_frame(f)
            
        for key in filter(lambda x: x not in self.SDI and x not in dontwrite,
                          self.realkeys()):
            if not isascii(self[key]): enc = 1
            else: enc = 3
            f = mutagen.id3.TXXX(
                encoding=enc, text=self[key].split("\n"),
                desc=u"QuodLibet::%s" % key)
            tag.loaded_frame(f)

        if "genre" in self:
            if not isascii(self["genre"]): enc = 1
            else: enc = 3
            t = self["genre"].split("\n")
            tag.loaded_frame(mutagen.id3.TCON(encoding=enc, text=t))
        else:
            try: del(tag["TCON"])
            except KeyError: pass

        tag.delall("COMM:")
        if "comment" in self:
            if not isascii(self["comment"]): enc = 1
            else: enc = 3
            t = self["comment"].split("\n")
            tag.loaded_frame(mutagen.id3.COMM(
                encoding=enc, text=t, desc=u"", lang="\x00\x00\x00"))

        for k in ["normalize", "album", "track"]:
            try: del(tag["RVA2:"+k])
            except KeyError: pass

        for k in ["track_peak", "track_gain", "album_peak", "album_gain"]:
            # Delete Foobar droppings.
            try: del(tag["TXXX:replaygain_" + k])
            except KeyError: pass

        for k in ["track", "album"]:
            if ('replaygain_%s_gain' % k) in self:
                gain = float(self["replaygain_%s_gain" % k].split()[0])
                try: peak = float(self["replaygain_%s_peak" % k])
                except (ValueError, KeyError): peak = 0
                f = mutagen.id3.RVA2(desc=k, channel=1, gain=gain, peak=peak)
                tag.loaded_frame(f)

        for key in self.BRAINZ:
            try: del(tag["TXXX:" + key])
            except KeyError: pass
        for key in self.ZNIARB:
            if key in self:
                f = mutagen.id3.TXXX(
                    encoding=0, text=self[key].split("\n"),
                    desc=self.ZNIARB[key])
                tag.loaded_frame(f)

        if (config.getboolean("editing", "save_to_songs") and
            (self["~#rating"] != 0.5 or self["~#playcount"] != 0)):
            email = config.get("editing", "save_email").strip()
            email = email or const.EMAIL
            t = mutagen.id3.POPM(email=email,
                                 rating=int(255*self["~#rating"]),
                                 count=self["~#playcount"])
            tag.loaded_frame(t)

        tag.save(self["~filename"])
        self.sanitize()

    def get_format_cover(self):
        f = tempfile.NamedTemporaryFile()
        tag = mutagen.id3.ID3(self["~filename"])
        for frame in tag.getall("APIC"):
            f.write(frame.data)
            f.flush()
            f.seek(0, 0)
            return f
        else:
            f.close()
            return None

info = MP3File
