# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from formats.audio import AudioFile, AudioPlayer

try: import pyid3lib, mad
except ImportError: extensions = []
else: extensions = [".mp3", ".mp2", ".mpg", ".mpeg"]

class MP3File(AudioFile):

    # http://www.unixgods.org/~tilo/ID3/docs/ID3_comparison.html
    # http://www.id3.org/id3v2.4.0-frames.txt
    IDS = { "TIT1": "genre",
            "TIT2": "title",
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
            "WOAR": "website",
            "TOLY": "author",
            "COMM": "comment",
            }

    INVERT_IDS = dict([(v, k) for k, v in IDS.iteritems()])
            
    def __init__(self, filename):
        tag = pyid3lib.tag(filename)
        date = ["", "", ""]

        for frame in tag:
            if frame["frameid"] == "TDAT" and len(frame["text"]) == 4:
                date[1] = frame["text"][0:2]
                date[2] = frame["text"][2:4]
                continue
            elif frame["frameid"] == "TYER" and len(frame["text"]) == 4:
                date[0] = frame["text"]
                continue
            elif frame["frameid"] == "APIC" and frame["data"]:
                self["~picture"] = "y"
                continue
            elif frame["frameid"] == "COMM":
                if frame["description"].startswith("QuodLibet::"):
                    name = frame["description"][11:]
                elif frame["description"] == "ID3v1 Comment": continue
                else: name = "comment"
            else: name = self.IDS.get(frame["frameid"], "").lower()

            if not name: continue

            try:
                text = frame["text"]
                if not text: continue
                for codec in ["utf-8", "shift-jis", "big5", "iso-8859-1"]:
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

        md = mad.MadFile(filename)
        self["~#length"] = md.total_time() // 1000
        if date[0]: self["date"] = "-".join(filter(None, date))
        self.sanitize(filename)

    def write(self):
        import pyid3lib
        tag = pyid3lib.tag(self['~filename'])

        ql_comments = [i for i, frame in enumerate(tag)
                       if (frame["frameid"] == "COMM" and
                           frame["description"].startswith("QuodLibet::"))]
        ql_comments.reverse()
        for comm in ql_comments: del(tag[comm])
        
        for key, id3name in self.INVERT_IDS.items():
            try:
                while True: tag.remove(id3name)
            except ValueError: pass
            if key in self:
                if self.unknown(key): continue
                for value in self.list(key):
                    value = value.encode("utf-8")
                    tag.append({'frameid': id3name, 'text': value })

        for key in filter(lambda x: x not in self.INVERT_IDS and x != "date",
                          self.realkeys()):
            for value in self.list(key):
                value = value.encode('utf-8')
                tag.append({'frameid': "COMM", 'text': value,
                            'description': "QuodLibet::%s" % key})

        for date in self.list("date"):
            y, m, d = (date + "--").split("-")[0:3]
            if y:
                try:
                    while True: tag.remove("TYER")
                except ValueError: pass
                tag.append({'frameid': "TYER", 'text': str(y)})
            if m and d:
                try:
                    while True: tag.remove("TDAT")
                except ValueError: pass
                tag.append({'frameid': "TDAT", 'text': str(m+d)})
        tag.update()
        self.sanitize()

class MP3Player(AudioPlayer):
    def __init__(self, dev, song):
        import mad
        filename = song['~filename']
        AudioPlayer.__init__(self)
        self.dev = dev
        self.audio = mad.MadFile(filename)
        self.dev.set_info(self.audio.samplerate(), 2)
        self.length = self.audio.total_time()
        self.replay_gain(song)

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.seek_time(int(ms))

    def next(self):
        if self.stopped: raise StopIteration
        buff = self.audio.read(256)
        if buff is None: raise StopIteration
        if self.scale != 1:
            buff = audioop.mul(buff, 2, self.scale)
        self.dev.play(buff)
        return self.audio.current_time()

info = MP3File
player = MP3Player
