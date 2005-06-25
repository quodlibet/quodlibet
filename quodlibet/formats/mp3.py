# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Niklas Janlert 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from formats.audio import AudioFile, AudioPlayer
import config
import re
import tempfile
try: import eyeD3, mad
except ImportError: extensions = []
else: extensions = [".mp3", ".mp2"]

# ID3 is absolutely the worst thing ever.

class MP3File(AudioFile):

    # http://www.unixgods.org/~tilo/ID3/docs/ID3_comparison.html
    # http://www.id3.org/id3v2.4.0-frames.txt
    IDS = { "TIT2": "title",
            "TIT3": "version",
            "TPE1": "artist",
            "TPE2": "performer", 
            "TPE3": "conductor",
            "TPE4": "arranger",
            "TEXT": "lyricist",
            "TCOM": "composer",
            "TENC": "encodedby",
            "TLAN": "language",
            "TALB": "album",
            "TRCK": "tracknumber",
            "TPOS": "discnumber",
            "TSRC": "isrc",
            "TCOP": "copyright",
            "TPUB": "organization",
            "USER": "license",
            "TSST": "part",
            "WOAR": "website",
            "TOLY": "author",
            "COMM": "comment",
            "TCON": "genre",
            "TMOO": "mood",
            "TBPM": "bpm",
            }
    SDI = dict([(v, k) for k, v in IDS.iteritems()])

    GENRES = { "0": "Blues",
               "1": "Classic Rock",
               "2": "Country",
               "3": "Dance",
               "4": "Disco",
               "5": "Funk",
               "6": "Grunge",
               "7": "Hip-Hop",
               "8": "Jazz",
               "9": "Metal",
               "10": "New Age",
               "11": "Oldies",
               "12": "Other",
               "13": "Pop",
               "14": "R&B",
               "15": "Rap",
               "16": "Reggae",
               "17": "Rock",
               "18": "Techno",
               "19": "Industrial",
               "20": "Alternative",
               "21": "Ska",
               "22": "Death Metal",
               "23": "Pranks",
               "24": "Soundtrack",
               "25": "Euro-Techno",
               "26": "Ambient",
               "27": "Trip-Hop",
               "28": "Vocal",
               "29": "Jazz+Funk",
               "30": "Fusion",
               "31": "Trance",
               "32": "Classical",
               "33": "Instrumental",
               "34": "Acid",
               "35": "House",
               "36": "Game",
               "37": "Sound Clip",
               "38": "Gospel",
               "39": "Noise",
               "40": "AlternRock",
               "41": "Bass",
               "42": "Soul",
               "43": "Punk",
               "44": "Space",
               "45": "Meditative",
               "46": "Instrumental Pop",
               "47": "Instrumental Rock",
               "48": "Ethnic",
               "49": "Gothic",
               "50": "Darkwave",
               "51": "Techno-Industrial",
               "52": "Electronic",
               "53": "Pop-Folk",
               "54": "Eurodance",
               "55": "Dream",
               "56": "Southern Rock",
               "57": "Comedy",
               "58": "Cult",
               "59": "Gangsta",
               "60": "Top 40",
               "61": "Christian Rap",
               "62": "Pop/Funk",
               "63": "Jungle",
               "64": "Native American",
               "65": "Cabaret",
               "66": "New Wave",
               "67": "Psychadelic",
               "68": "Rave",
               "69": "Showtunes",
               "70": "Trailer",
               "71": "Lo-Fi",
               "72": "Tribal",
               "73": "Acid Punk",
               "74": "Acid Jazz",
               "75": "Polka",
               "76": "Retro",
               "77": "Musical",
               "78": "Rock & Roll",
               "CR": "Cover",
               "RX": "Remix",
               }

    CODECS = ["utf-8"]
    try: CODECS.extend(config.get("editing", "id3encoding").strip().split())
    except: pass # Uninitialized config...
    CODECS.append("iso-8859-1")

    SERNEG = dict([(v, k) for k, v in GENRES.iteritems()])

    # Matches "(1)", "(99)Dark Ambience" and "Blues".
    GENRE_RE = re.compile(r"(?:\((?P<id>[0-9]+|RX|CR)\))?(?P<str>.+)?")
            
    def __init__(self, filename):
        tag = eyeD3.Tag(eyeD3.ID3_V2_4)
        tag.link(filename)
        date = ["", "", ""]

        for frame in tag.frames:
            if frame.header.id == "TDAT" and len(frame.text) == 4:
                date[1] = frame.text[0:2]
                date[2] = frame.text[2:4]
                continue
            elif frame.header.id == "TYER" and len(frame.text) == 4:
                date[0] = frame.text
                continue
            elif frame.header.id == "APIC" and len(frame.imageData):
                self["~picture"] = "y"
                continue
            elif frame.header.id == "TCON":
                self.__fix_genre(frame.text)
                continue            
            elif frame.header.id in ["COMM", "TXXX"]:
                if frame.description.startswith("QuodLibet::"):
                    name = frame.description[11:]
                elif frame.description == "ID3v1 Comment": continue
                else: name = "comment"
            else: name = self.IDS.get(frame.header.id, "").lower()

            if not name: continue

            try:
                id3id = frame.header.id
                if id3id.startswith("T"): text = frame.text
                elif id3id == "COMM": text = frame.comment
                elif id3id.startswith("W"):
                    dec = eyeD3.id3EncodingToString(frame.encoding)
                    text = frame.url[1:].decode(dec)
                elif id3id == "USER":
                    dec = eyeD3.id3EncodingToString(frame.encoding)
                    text = frame.data[1:].decode(dec)
                else: continue

                if not text: continue
                if not isinstance(text, unicode):
                    assert isinstance(text, unicode)
                if frame.encoding == eyeD3.LATIN1_ENCODING:
                    text = text.encode('iso-8859-1')
                    for codec in self.CODECS:
                        try: text = text.decode(codec)
                        except (UnicodeError, LookupError): pass
                        else: break
                    else: continue
                if name in self:
                    if text in self[name]: pass
                    elif self[name] in text: self[name] = text
                    else: self[name] += "\n" + text
                else: self[name] = text
                self[name] = self[name].strip()
            except: pass

        d = tag.getDate()
        if d and len(d): d = d[0]
        if d: date = list(d.getDate().split("T")[0].split("-")) + [None, None]

        md = mad.MadFile(filename)
        # Avoid garbage at the start of the file.
        md.seek_time(md.total_time()); md.read()
        self["~#length"] = md.total_time() // 1000
        md.seek_time(md.total_time() / 2); md.read()
        bitrates = [md.bitrate() for i in range(10) if md.read()]
        self["~#bitrate"] = int(sum(bitrates) / len(bitrates))
        if date[0]: self["date"] = "-".join(filter(None, date))
        self.sanitize(filename)

    def __fix_genre(self, gstr):
        # http://www.id3.org/id3v2.3.0.html#TCON
        # TCON is in one of the following formats:
        # (xx)
        # (xx)Refinement
        # Refinement

        # Where 'xx' is the genre numeric ID. De facto 'Refinement' has
        # become the same as the ID so if it's present ignore the numeric one.
        # In theory there can be more than one genre per frame. I have
        # never seen this, and this doesn't yet support it.

        # This is only for reading them. Writing should work fine with
        # existing code, since we'll just write out the strings once
        # per frame.

        # strip null string.. might be needed? -- niklasjanlert
        gstr = gstr.rstrip("\x00")

        genreid, genrename = self.GENRE_RE.match(gstr).groups()
        if genrename: genrename = genrename.strip()

        if not genreid:
            try: genreid = str(int(gstr)) # Try id3v1 style..
            except ValueError: pass

        if genreid or genreid == 0: # ID3v1 style 'Blues' == 0.
            genreid = str(int(genreid)) # "01" to "1"
            try: self.add("genre", self.GENRES[genreid])
            except KeyError: pass

        if genrename and genrename not in self.list("genre"):
            self.add("genre", genrename)

    def write(self):
        tag = eyeD3.Tag()
        tag.link(self['~filename'])

        for frame in tag.frames[eyeD3.COMMENT_FID]:
            if frame.description.startswith("QuodLibet::"):
                tag.frames.remove(frame)
        for frame in tag.frames[eyeD3.USERTEXT_FID]:
            if frame.description.startswith("QuodLibet::"):
                tag.frames.remove(frame)

        for key, id3name in self.SDI.items():
            for frame in tag.frames[id3name]:
                tag.frames.remove(frame)
            if id3name == "COMM" and key in self:
                h = eyeD3.FrameHeader(tag.frames.tagHeader)
                h.id = "COMM"
                f = eyeD3.CommentFrame(
                    h, comment=unicode(self[key]), description=u"", lang="")
                tag.frames.addFrame(f)
            else:
                for value in self.list(key):
                    h = eyeD3.FrameHeader(tag.frames.tagHeader)
                    h.id = id3name
                    f = eyeD3.TextFrame(h, text=unicode(value))
                    tag.frames.addFrame(f)

        for key in filter(lambda x: x not in self.SDI and x != "date",
                          self.realkeys()):
            for value in self.list(key):
                h = eyeD3.FrameHeader(tag.frames.tagHeader)
                h.id = "TXXX"
                f = eyeD3.UserTextFrame(
                    h, text=unicode(value), description=u"QuodLibet::%s" % key)
                tag.frames.addFrame(f)

        for date in self.list("date"):
            y, m, d = (date + "--").split("-")[0:3]
            if y and m and d:
                tag.setDate(year=y, month=m, dayOfMonth=d)
            elif y:
                tag.setDate(year=y)
        tag.setVersion(eyeD3.ID3_V2_4)
        tag.setTextEncoding(eyeD3.UTF_8_ENCODING)
        tag.update(eyeD3.ID3_V2_4)
        self.sanitize()

    def get_format_cover(self):
        f = tempfile.NamedTemporaryFile()
        tag = eyeD3.Tag(eyeD3.ID3_V2_4)
        tag.link(self['~filename'])
        for frame in tag.frames[eyeD3.IMAGE_FID]:
            f.write(frame.imageData)
            f.flush()
            f.seek(0, 0)
            return f
        else:
            f.close()
            return None

class MP3Player(AudioPlayer):
    def __init__(self, dev, song):
        import mad
        filename = song['~filename']
        AudioPlayer.__init__(self)
        self.dev = dev
        audio = mad.MadFile(filename)
        # Lots of MP3s report incorrect bitrates/samplerates/lengths if
        # the ID3 tag is busted in whatever way the ID3 tag reader is
        # using. Seek to the end of the file to get relaible information.
        audio.seek_time(audio.total_time())
        audio.read()
        self.__expected_sr = audio.samplerate()
        self.dev.set_info(self.__expected_sr, 2)
        self.length = audio.total_time()
        # Then, reload so we don't get repeat audio.
        self.audio = mad.MadFile(filename)
        self.replay_gain(song)

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.seek_time(int(ms))

    def next(self):
        if self.stopped: raise StopIteration
        buff = self.audio.read(256)
        if self.audio.samplerate() != self.__expected_sr:
            print "W: Skipping what doesn't look like audio data..."
            while self.audio.samplerate() != self.__expected_sr and buff:
                buff = self.audio.read(256)
            buff = self.audio.read(256)
        if buff is None: raise StopIteration
        self.dev.play(buff)
        return self.audio.current_time()

info = MP3File
player = MP3Player
