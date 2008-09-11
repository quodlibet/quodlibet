# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Niklas Janlert 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import mutagen.id3
import tempfile

from quodlibet import config
from quodlibet import const

from quodlibet.formats._audio import AudioFile

def isascii(s):
    return ((len(s) == 0) or (ord(max(s)) < 128))

class ID3hack(mutagen.id3.ID3):
    "Override 'correct' behavior with desired behavior"
    def add(self, tag):
        if len(type(tag).__name__) == 3:
            tag = type(tag).__base__(tag)
        if tag.HashKey in self and tag.FrameID[0] == "T":
            self[tag.HashKey].extend(tag[:])
        else: self[tag.HashKey] = tag

# ID3 is absolutely the worst thing ever.
class ID3File(AudioFile):

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
            "TSST": "discsubtitle",
            "TOLY": "author",
            "TMOO": "mood",
            "TBPM": "bpm",
            "TDRC": "date",
            "TDOR": "originaldate",
            "TOAL": "originalalbum",
            "TOPE": "originalartist",
            "WOAR": "website",
            "TSOP": "artistsort",
            "TSOA": "albumsort",
            "TSOT": "artistsort",
            "TMED": "media",
            "TCMP": "compilation",
            # "language" should not make to TLAN. TLAN requires
            # an ISO language code, and QL tags are freeform.
            }
    SDI = dict([(v, k) for k, v in IDS.iteritems()])

    # At various times, information for this came from
    # http://musicbrainz.org/docs/specs/metadata_tags.html
    # http://bugs.musicbrainz.org/ticket/1383
    # http://musicbrainz.org/doc/MusicBrainzTag
    TXXX_MAP = {
        u"MusicBrainz Artist Id": "musicbrainz_artistid",
        u"MusicBrainz Album Id": "musicbrainz_albumid",
        u"MusicBrainz Album Artist Id": "musicbrainz_albumartistid",
        u"MusicBrainz TRM Id": "musicbrainz_trmid",
        u"MusicIP PUID": "musicip_puid",
        u"MusicMagic Fingerprint": "musicip_fingerprint",
        u"MusicBrainz Album Status": "musicbrainz_albumstatus",
        u"MusicBrainz Album Type": "musicbrainz_albumtype",
        u"MusicBrainz Album Release Country": "releasecountry",
        u"MusicBrainz Disc Id": "musicbrainz_discid",
        u"ASIN": "asin",
        u"ALBUMARTISTSORT": "albumartistsort",
        u"BARCODE": "barcode",
        }
    PAM_XXXT = dict([(v, k) for k, v in TXXX_MAP.iteritems()])

    CODECS = ["utf-8"]
    try: CODECS.extend(config.get("editing", "id3encoding").strip().split())
    except: pass # Uninitialized config...
    CODECS.append("iso-8859-1")

    Kind = None

    def __init__(self, filename):
        audio = self.Kind(filename, ID3=ID3hack)
        tag = audio.tags or {}

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
                elif frame.email == config.get("editing", "save_email"):
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
                elif frame.desc in self.TXXX_MAP:
                    name = self.TXXX_MAP[frame.desc]
                else: continue
            elif frame.FrameID == "RVA2":
                self.__process_rg(frame)
                continue
            elif frame.FrameID == "TMCL":
                for role, name in frame.people:
                    role = role.encode('utf-8')
                    self.add("performer:" + role, name)
                continue
            else: name = self.IDS.get(frame.FrameID, "").lower()

            name = name.lower()

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

        self.setdefault("~#length", int(audio.info.length))
        try: self.setdefault("~#bitrate", int(audio.info.bitrate))
        except AttributeError: pass

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
                    "TMCL",
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
                    tag.add(Kind(url=t))
            else: tag.add(Kind(encoding=enc, text=text))

        dontwrite = ["genre", "comment", "replaygain_album_peak",
                     "replaygain_track_peak", "replaygain_album_gain",
                     "replaygain_track_gain", "musicbrainz_trackid",
                     ] + self.TXXX_MAP.values()

        if "musicbrainz_trackid" in self.realkeys():
            f = mutagen.id3.UFID(owner="http://musicbrainz.org",
                  data=self["musicbrainz_trackid"])
            tag.add(f)
            
        mcl = mutagen.id3.TMCL(encoding=3, people=[])

        for key in filter(lambda x: x not in self.SDI and x not in dontwrite,
                          self.realkeys()):
            if not isascii(self[key]): enc = 1
            else: enc = 3

            if key.startswith("performer:"):
                mcl.people.append([key.split(":", 1)[1], self[key]])
                continue

            f = mutagen.id3.TXXX(
                encoding=enc, text=self[key].split("\n"),
                desc=u"QuodLibet::%s" % key)
            tag.add(f)

        if mcl.people:
            tag.add(mcl)

        if "genre" in self:
            if not isascii(self["genre"]): enc = 1
            else: enc = 3
            t = self["genre"].split("\n")
            tag.add(mutagen.id3.TCON(encoding=enc, text=t))
        else:
            try: del(tag["TCON"])
            except KeyError: pass

        tag.delall("COMM:")
        if "comment" in self:
            if not isascii(self["comment"]): enc = 1
            else: enc = 3
            t = self["comment"].split("\n")
            tag.add(mutagen.id3.COMM(
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
                tag.add(f)

        for key in self.TXXX_MAP:
            try: del(tag["TXXX:" + key])
            except KeyError: pass
        for key in self.PAM_XXXT:
            if key in self:
                f = mutagen.id3.TXXX(
                    encoding=0, text=self[key].split("\n"),
                    desc=self.PAM_XXXT[key])
                tag.add(f)

        if (config.getboolean("editing", "save_to_songs") and
            (self["~#rating"] != 0.5 or self["~#playcount"] != 0)):
            email = config.get("editing", "save_email").strip()
            email = email or const.EMAIL
            t = mutagen.id3.POPM(email=email,
                                 rating=int(255*self["~#rating"]),
                                 count=self["~#playcount"])
            tag.add(t)

        tag.save(self["~filename"])
        self.sanitize()

    def get_format_cover(self):
        try: tag = mutagen.id3.ID3(self["~filename"])
        except (EnvironmentError, mutagen.id3.error):
            return None
        else:
            for frame in tag.getall("APIC"):
                f = tempfile.NamedTemporaryFile()
                f.write(frame.data)
                f.flush()
                f.seek(0, 0)
                return f
            else:
                f.close()
                return None
