# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sre, stat, string
import gettext
_ = gettext.gettext

def mtime(filename):
    try: return os.stat(filename)[stat.ST_MTIME]
    except OSError: return 0
os.path.mtime = mtime

# Make a directory, including all directories below it.
def mkdir(dir):
    if not os.path.isdir(dir):
        os.makedirs(dir)

# Escape a string in a manner suitable for XML/Pango.
def escape(str):
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# Unescape a string that was escaped for XML/Pango.
def unescape(str):
    return str.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

# A better version of sre.escape, that doesn't go nuts on Unicode.
def re_esc(str):
    return "".join(map(
        lambda a: (a in "/.^$*+?{,}\\[]|()<>#=!:" and "\\" + a) or a, str))
sre.escape = re_esc

# Check whether or not we can support various formats.
def check_mp3():
    try: import pyid3lib, mad
    except ImportError: return False
    else: return True

def check_ogg():
    try: import ogg.vorbis
    except ImportError: return False
    else: return True

def check_flac():
    try: import flac.decoder
    except ImportError: return False
    else: return True

def check_mod():
    try: import modplug
    except ImportError: return False
    else: return True

def check_mpc():
    try: import musepack
    except ImportError: return False
    else: return True

def parse_time(timestr):
    try:
        return reduce(lambda s, a: s * 60 + int(a),
                      sre.split(":|\\.", timestr), 0)
    except:
        return 0

def format_time(time):
    if time > 3600: # 1 hour
        return _("%d:%02d:%02d") % (time // 3600,
                                    (time % 3600) // 60, time % 60)
    else:
        return _("%d:%02d") % (time // 60, time % 60)

def format_time_long(time):
    if time < 1: return _("No time information")
    time_str = ""
    if time > 365 * 24 * 60 * 60:
        years = (time // (365 * 24 * 60 * 60))
        if years != 1: time_str += _("%d years, ") % years
        else: time_str += _("1 year, ")
        time = time % (365 * 24 * 60 * 60)
    if time > 24 * 60 * 60:
        days = (time // (24 * 60 * 60))
        if days != 1: time_str += _("%d days, ") % days
        else: time_str += _("1 day, ")
        time = time % (24 * 60 * 60)
    if time > 60 * 60:
        hours = (time // (60 * 60))
        if hours != 1: time_str += _("%d hours, ") % hours
        else: time_str += _("1 hour, ")
        time = time % (60 * 60)
    if time > 60:
        mins = (time // 60)
        if mins != 1: time_str += _("%d minutes, ") % mins
        else: time_str += _("1 minute, ")
        time = time % 60
    # only include seconds if we don't have hours (or greater)
    if time and len(time_str) <= len(_("xx minutes, ")):
        if time != 1: time_str += _("%d seconds") % time
        else: time_str += _("1 second")
        
    return time_str.rstrip(" ,")

def fscoding():
    if "CHARSET" in os.environ: return os.environ["CHARSET"]
    elif "G_BROKEN_FILENAMES" in os.environ:
        cset = os.environ.get("LC_CTYPE", "foo.utf-8")
        if "." in cset: return cset.split(".")[-1]
        else: return "utf-8"
    else: return "utf-8"

def decode(s):
    try: return s.decode("utf-8")
    except UnicodeError:
        try: return s.decode("utf-8", "replace") + " " + _("[Invalid Unicode]")
        except UnicodeError: return _("[Invalid Unicode]")

def encode(s):
    try: return s.encode("utf-8")
    except UnicodeError:
        try: return s.encode("utf-8", "replace") + " " + _("[Invalid Unicode]")
        except UnicodeError: return _("[Invalid Unicode]")

def title(string):
    if not string: return ""
    new_string = string[0].capitalize()
    cap = False
    for s in string[1:]:
        if s.isspace(): cap = True
        elif cap and s.isalpha():
            cap = False
            s = s.capitalize()
        new_string += s
    return new_string

def iscommand(s):
    if s == "" or "/" in s:
        return os.path.exists(s)
    else:
        s = s.split()[0]
        for p in os.environ["PATH"].split(":"):
            p2 = os.path.join(p, s)
            if os.path.exists(p2): return True
        else: return False

# Split a string on ;s and ,s.
def split_value(s, splitters = ",;&"):
    values = s.split("\n")
    for spl in splitters:
        new_values = []
        for v in values:
            new_values.extend(map(string.strip, v.split(spl)))
        values = new_values
    return values

def split_title(s, splitters = ",;&"):
    title, subtitle = find_subtitle(s)
    if not subtitle: return (s, [])
    else:
        return (title.strip(), split_value(subtitle, splitters))

def split_people(s, splitters = ",;&"):
    title, subtitle = find_subtitle(s)
    if not subtitle:
        parts = s.split(" ")
        if len(parts) > 2:
            for feat in ["feat.", "featuring", "feat", "with", "w/"]:
                try:
                    i = map(string.lower, parts).index(feat)
                    orig = " ".join(parts[:i])
                    others = " ".join(parts[i+1:])
                    return (orig, split_value(others, splitters))
                except (ValueError, IndexError): pass
        return (s, [])
    else:
        for feat in ["feat.", "featuring", "feat", "with", "w/"]:
            if subtitle.startswith(feat):
                subtitle = subtitle.replace(feat, "", 1)
                subtitle.lstrip()
                break
        values = split_value(subtitle, splitters)
        return (title.strip(), values)

def split_album(s):
    name, disc = find_subtitle(s)
    if not disc:
        parts = s.split(" ")
        if len(parts) > 2:
            lower = parts[-2].lower()
            if "disc" in lower or "disk" in lower:
                return (" ".join(parts[:-2]), parts[-1])
        return (s, None)
    else:
        parts = disc.split()
        if (len(parts) == 2 and
            parts[0].lower() in ["disc", "disk", "cd", "vol", "vol."]):
            try: return (name, parts[1])
            except: return (s, None)

def find_subtitle(title):
    if isinstance(title, str): title = unicode(title, 'utf-8')
    for pair in [u"[]", u"()", u"~~", u"--", u"\u301c\u301c"]:
        if pair[0] in title and title.endswith(pair[1]):
            r = len(pair[1])
            l = title[0:-r].rindex(pair[0])
            if l != 0:
                subtitle = title[l+len(pair[0]):-r]
                title = title[:l]
                return title.rstrip(), subtitle
    else: return title, None

def format_string(format, d):
    i = 0
    output = ""
    in_cond = False
    while i < len(format):
        c = format[i]
        if c == "%" and i != len(format) - 1 and format[i + 1] == "(":
            i += 2
            tag = ""
            while format[i] != ")" and i < len(format):
                tag += format[i]
                i += 1
            output += d.get(tag, "Unknown")
        elif c == "?":
            if in_cond: in_cond = False
            elif format[i + 1] == "(":
                i += 2
                tag = ""
                while format[i] != ")" and i < len(format):
                    tag += format[i]
                    i += 1
                if tag not in d:
                    while format[i] != "?": i += 1
                else: in_cond = True
            else: output += "?"
        else: output += c
        i += 1
    return output

def unexpand(filename):
    if filename.startswith(os.path.expanduser("~")):
        filename = filename.replace(os.path.expanduser("~"), "~", 1)
    return filename

class PatternFromFile(object):
    def __init__(self, pattern):
        self.compile(pattern)

    def compile(self, pattern):
        self.headers = []
        self.slashes = len(pattern) - len(pattern.replace('/','')) + 1
        self.pattern = None
        # patterns look like <tagname> non regexy stuff <tagname> ...
        pieces = sre.split(r'(<[A-Za-z0-9_]+>)', pattern)
        override = { '<tracknumber>': r'\d\d?', '<discnumber>': r'\d\d?' }
        for i, piece in enumerate(pieces):
            if not piece: continue
            if piece[0]+piece[-1] == '<>' and piece[1:-1].isalnum():
                piece = piece.lower()   # canonicalize to lowercase tag names
                pieces[i] = '(?P%s%s)' % (piece, override.get(piece, '.+'))
                self.headers.append(piece[1:-1].encode("ascii", "replace"))
            else:
                pieces[i] = re_esc(piece)

        # some slight magic to anchor searches "nicely"
        # nicely means if it starts with a <tag>, anchor with a /
        # if it ends with a <tag>, anchor with .xxx$
        # but if it's a <tagnumber>, don't bother as \d+ is sufficient
        # and if it's not a tag, trust the user
        if pattern.startswith('<') and not pattern.startswith('<tracknumber>')\
                and not pattern.startswith('<discnumber>'):
            pieces.insert(0, '/')
        if pattern.endswith('>') and not pattern.endswith('<tracknumber>')\
                and not pattern.endswith('<discnumber>'):
            pieces.append(r'(?:\.\w+)$')

        self.pattern = sre.compile(''.join(pieces))

    def match(self, song):
        if isinstance(song, dict):
            song = song['~filename'].decoded
        # only match on the last n pieces of a filename, dictated by pattern
        # this means no pattern may effectively cross a /, despite .* doing so
        matchon = '/'+'/'.join(song.split('/')[-self.slashes:])
        match = self.pattern.search(matchon)

        # dicts for all!
        if match is None: return {}
        else: return match.groupdict()

class FileFromPattern(object):
    def __init__(self, pattern, tagre=sre.compile(r'(<\w+(?:\~\w+)*>)')):
        if '/' in pattern and not pattern.startswith('/'):
            raise ValueError("Pattern %r is not rooted" % pattern)
        self.pattern = pattern
        self.pieces = tagre.split(pattern)

    def match(self, song, tagre=sre.compile(r'<\w+(?:\~\w+)*>')):
        format = { 'tracknumber': '%02d', 'discnumber': '%d' }
        override = { 'tracknumber': '~#track', 'discnumber': '~#disc' }
        newname = []
        for piece in self.pieces:
            if not piece: continue
            if tagre.match(piece):
                piece = piece[1:-1]
                texts = []
                for part in piece.split('~'):
                    text = song.comma(override.get(part, part))
                    try: text = format.get(part, '%s') % text
                    except TypeError: pass
                    texts.append(text)
                text = ' - '.join(filter(None, texts))
                try: text = format.get(piece, '%s') % text
                except TypeError: pass
                newname.append(text.replace('/', '_'))
            else:
                newname.append(piece)

        # simple magic to decide whether to append the extension
        # if the pattern has no . in it, or if it has a > (probably a tag)
        #   after the last . or if the last character is the . append .foo
        pat = self.pattern
        if pat and ('.' not in pat or pat.endswith('.') or
                '>' in pat[pat.rfind('.'):]):
            oldname = song('~basename')
            newname.append(oldname[oldname.rfind('.'):])
        return ''.join(newname)
