# Copyright 2004-2012 Joe Wreschnig, Michael Urman, Niklas Janlert,
#                     Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import mutagen.id3
import tempfile

from quodlibet import config, const, print_d
from quodlibet.formats._audio import AudioFile
from quodlibet.util.massagers import LanguageMassager

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

class ID3bug(mutagen.id3.ID3):
    def load(self, *args, **kwargs):
        # work arround mutagen bug by throwing away unknown 2.3 frames on load
        # http://code.google.com/p/mutagen/issues/detail?id=97
        super(ID3bug, self).load(*args, **kwargs)
        if self.version == (2, 3, 0) and mutagen.version < (1, 21):
            del self.unknown_frames[:]

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
            "TSOT": "titlesort",
            "TSO2": "albumartistsort",
            "TSOC": "composersort",
            "TMED": "media",
            "TCMP": "compilation",
            # TLAN requires an ISO 639-2 language code, check manually
            #"TLAN": "language"
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
        tag = audio.tags or mutagen.id3.ID3()

        for frame in tag.values():
            if frame.FrameID == "APIC" and len(frame.data):
                self["~picture"] = "y"
                continue
            elif frame.FrameID == "TCON":
                self["genre"] = "\n".join(frame.genres)
                continue
            elif frame.FrameID == "TLEN":
                try: length = +frame // 1000
                except ValueError: continue
                # ignore TLEN <= 0 [issue 222]
                if length > 0:
                    self["~#length"] = length
                continue
            elif (frame.FrameID == "UFID" and
                  frame.owner == "http://musicbrainz.org"):
                self["musicbrainz_trackid"] = frame.data
                continue
            elif frame.FrameID == "POPM":
                rating = frame.rating / 255.0
                if frame.email == const.EMAIL:
                    try: self.setdefault("~#playcount", frame.count)
                    except AttributeError: pass
                    self.setdefault("~#rating", rating)
                elif frame.email == config.get("editing", "save_email"):
                    try: self["~#playcount"] = frame.count
                    except AttributeError: pass
                    self["~#rating"] = rating
                continue
            elif frame.FrameID == "COMM" and frame.desc == "":
                name = "comment"
            elif frame.FrameID in ["COMM", "TXXX"]:
                if frame.desc.startswith("QuodLibet::"):
                    name = frame.desc[11:]
                elif frame.desc in self.TXXX_MAP:
                    name = self.TXXX_MAP[frame.desc]
                else: continue
            elif frame.FrameID == "RVA2":
                self.__process_rg(frame)
                continue
            elif frame.FrameID == "TMCL":
                for role, name in frame.people:
                    key = self.__validate_name("performer:" + role)
                    if key:
                        self.add(key, name)
                continue
            elif frame.FrameID == "TLAN":
                self["language"] = "\n".join(frame.text)
                continue
            else: name = self.IDS.get(frame.FrameID, "").lower()

            name = self.__validate_name(name)
            if not name:
                continue
            name = name.lower()

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

            # to catch a missing continue above
            del name

        # foobar2000 writes long dates in a TXXX DATE tag, leaving the TDRC
        # tag out. Read the TXXX DATE, but only if the TDRC tag doesn't exist
        # to avoid reverting or duplicating tags in existing libraries.
        if audio.tags and "date" not in self:
            for frame in tag.getall('TXXX:DATE'):
                self["date"] = "\n".join(map(unicode, frame.text))

        # Read TXXX replaygain in case we don't have any (from RVA2)
        for k in ["track_peak", "track_gain", "album_peak", "album_gain"]:
            k = "replaygain_" + k
            if k not in self:
                for frame in tag.getall("TXXX:" + k):
                    self[k] = "\n".join(map(unicode, frame.text))

        self.setdefault("~#length", int(audio.info.length))
        try: self.setdefault("~#bitrate", int(audio.info.bitrate / 1000))
        except AttributeError: pass

        self.sanitize(filename)

    def __validate_name(self, k):
        """Returns a ascii string or None if the key isn't supported"""
        if isinstance(k, unicode):
            k = k.encode("utf-8")
        if not (k and "=" not in k and "~" not in k
                and k.encode("ascii", "replace") == k):
            return
        return k

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
        try: tag = ID3bug(self['~filename'])
        except mutagen.id3.error: tag = mutagen.id3.ID3()

        # prefill TMCL with the ones we can't read
        mcl = tag.get("TMCL", mutagen.id3.TMCL(encoding=3, people=[]))
        mcl.people = [(r, n) for (r, n) in mcl.people
                      if not self.__validate_name(r)]

        # delete all TXXX/COMM we can read except empty COMM
        for frame in ["COMM:", "TXXX:"]:
            for t in tag.getall(frame + "QuodLibet:"):
                if t.desc and self.__validate_name(t.desc):
                    del tag[t.HashKey]

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

        # Issue 439 - Only write valid ISO 639-2 codes to TLAN (else TXXX)
        tag.delall("TLAN")
        if "language" in self:
            langs = self["language"].split("\n")
            if all([lang in LanguageMassager.ISO_639_2 for lang in langs]):
                # Save value(s) to TLAN tag. Guaranteed to be ASCII here
                tag.add(mutagen.id3.TLAN(encoding=3, text=langs))
                dontwrite += ["language"]
            else:
                print_d("Not using invalid language code '%s' in TLAN" %
                        self["language"], context=self)

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

        # Delete old foobar replaygain and write new one
        for k in ["track_peak", "track_gain", "album_peak", "album_gain"]:
            k = "replaygain_" + k
            # Delete Foobar droppings.
            try: del(tag["TXXX:" + k])
            except KeyError: pass
            # Add new ones
            if k in self:
                tag.add(mutagen.id3.TXXX(
                        encoding=0, text=self[k].split("\n"),
                        desc=k))

        # we shouldn't delete all, but we use unknown ones as fallback, so make
        # sure they don't come back after reloading
        for t in tag.getall("RVA2"):
            if t.channel == 1:
                del tag[t.HashKey]

        for k in ["track", "album"]:
            if ('replaygain_%s_gain' % k) in self:
                try: gain = float(self["replaygain_%s_gain" % k].split()[0])
                except ValueError: gain=0
                try: peak = float(self["replaygain_%s_peak" % k])
                except (ValueError, KeyError): peak = 0
                # http://code.google.com/p/quodlibet/issues/detail?id=1027
                peak = max(min(1.9, peak), 0)
                gain = max(min(63.9, gain), -64)
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
            (self("~#rating") != const.DEFAULT_RATING or
            self.get("~#playcount", 0) != 0)):
            email = config.get("editing", "save_email").strip()
            email = email or const.EMAIL
            t = mutagen.id3.POPM(email=email,
                                 rating=int(255*self("~#rating")),
                                 count=self.get("~#playcount", 0))
            tag.add(t)

        tag.save(self["~filename"])
        self.sanitize()

    def get_format_cover(self):
        try: tag = mutagen.id3.ID3(self["~filename"])
        except (EnvironmentError, mutagen.id3.error):
            return None

        cover = None
        for frame in tag.getall("APIC"):
            cover = cover or frame
            if frame.type == 3:
                cover = frame
                break

        if cover:
            f = tempfile.NamedTemporaryFile()
            f.write(cover.data)
            f.flush()
            f.seek(0, 0)
            return f

