# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sre, stat, string, locale

# Convert a string from 'frm' encoding (or Unicode) to the native one.
# Only use this for console messages; PyGTK understands both Unicode
# and UTF-8 properly.
def to(string, frm = "utf-8"):
    enc = locale.getpreferredencoding()
    if isinstance(string, unicode): return string.encode(enc, "replace")
    else: return string.decode(frm).encode(enc, "replace")

def mtime(filename):
    try: return os.path.getmtime(filename)
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

def parse_time(timestr):
    try:
        return reduce(lambda s, a: s * 60 + int(a),
                      sre.split(":|\\.", timestr), 0)
    except (ValueError, sre.error):
        return 0

def format_size(size):
    if size >= 1024*1024 * 10:
        return "%.1fMB" % (float(size) / (1024*1024))
    elif size >= 1024*1024:
        return "%.2fMB" % (float(size) / (1024*1024))
    elif size >= 1024 * 10:
        return "%dKB" % int(size / 1024)
    elif size >= 1024:
        return "%.2fKB" % (float(size) / 1024)
    else:
        return "%dB" % size

def format_time(time):
    if time > 3600: # 1 hour
        return _("%d:%02d:%02d") % (time // 3600,
                                    (time % 3600) // 60, time % 60)
    else:
        return _("%d:%02d") % (time // 60, time % 60)

def format_time_long(time):
    if time < 1: return _("No time information")
    cutoffs = [
        (60, _("%d seconds"), _("1 second")),
        (60, _("%d minutes"), _("1 minute")),
        (24, _("%d hours"), _("1 hour")),
        (365, _("%d days"), _("1 day")),
        (None, _("%d years"), _("1 year")),
    ]
    time_str = []
    for divisor, plural, single in cutoffs:
        if time < 1: break
        if divisor is None: time, unit = 0, time
        else: time, unit = divmod(time, divisor)
        if unit == 1: time_str.append(single)
        else: time_str.append(plural % unit)
    time_str.reverse()
    if len(time_str) > 2: time_str.pop()
    return ", ".join(time_str)

def fscoding():
    if "CHARSET" in os.environ: return os.environ["CHARSET"]
    elif "G_BROKEN_FILENAMES" in os.environ:
        cset = os.environ.get("LC_CTYPE", "foo.utf-8")
        if "." in cset: return cset.split(".")[-1]
        else: return "utf-8"
    else: return "utf-8"

def fsdecode(s):
    if isinstance(s, unicode): return s
    else: return decode(s, fscoding())

def decode(s, charset = "utf-8"):
    try: return s.decode(charset)
    except UnicodeError:
        try:
            return s.decode(charset, "replace") + " " + _("[Invalid Encoding]")
        # FIXME: Can this happen?
        except UnicodeError: return _("[Invalid Encoding]")

def encode(s, charset = "utf-8"):
    try: return s.encode(charset)
    # FIXME: Can *this* happen?
    except UnicodeError:
        try:
            return (s+" " + _("[Invalid Encoding]")).encode(charset, "replace")
        # Can *THIS* happen?
        except UnicodeError: return _("[Invalid Encoding]")

def title(string):
    if not string: return ""
    new_string = string[0].capitalize()
    cap = False
    for s in string[1:]:
        if s.isspace(): cap = True
        elif cap and s.isalpha():
            cap = False
            s = s.capitalize()
        else: cap = False
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
    else: return (title.strip(), split_value(subtitle, splitters))

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
                subtitle = subtitle.replace(feat, "", 1).lstrip()
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
        else: return (s, None)

def find_subtitle(title):
    if isinstance(title, str): title = title.decode('utf-8', 'replace')
    for pair in [u"[]", u"()", u"~~", u"--", u"\u301c\u301c"]:
        if pair[0] in title[:-1] and title.endswith(pair[1]):
            r = len(pair[1])
            l = title[0:-r].rindex(pair[0])
            if l != 0:
                subtitle = title[l+len(pair[0]):-r]
                title = title[:l]
                return title.rstrip(), subtitle
    else: return title, None

def unexpand(filename):
    if filename == os.path.expanduser("~"): return "~"
    elif filename.startswith(os.path.expanduser("~/")):
        filename = filename.replace(os.path.expanduser("~/"), "~/", 1)
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
            song = song['~filename'].decode(fscoding(), "replace")
        # only match on the last n pieces of a filename, dictated by pattern
        # this means no pattern may effectively cross a /, despite .* doing so
        matchon = '/'+'/'.join(song.split('/')[-self.slashes:])
        match = self.pattern.search(matchon)

        # dicts for all!
        if match is None: return {}
        else: return match.groupdict()

class FileFromPattern(object):
    format = { 'tracknumber': '%02d', 'discnumber': '%d' }
    override = { 'tracknumber': '~#track', 'discnumber': '~#disc' }

    def __init__(self, pattern, filename = True):
        if filename and '/' in pattern and not pattern.startswith('/'):
            raise ValueError("Pattern %r is not rooted" % pattern)

        self.replacers = [self.Pattern(pattern)]
        # simple magic to decide whether to append the extension
        # if the pattern has no . in it, or if it has a > (probably a tag)
        #   after the last . or if the last character is the . append .foo
        if filename and pattern and (
            '.' not in pattern or pattern.endswith('.') or
            '>' in pattern[pattern.rfind('.'):]):
            self.replacers.append(self.ExtensionCopy())

    def match(self, song):
        return ''.join([r.match(song) for r in self.replacers])

    class ExtensionCopy(object):
        def match(self, song):
            oldname = song('~basename').decode(fscoding(), 'replace')
            return oldname[oldname.rfind('.'):]

    class Pattern(object):
        def __init__(self, pattern, tagre=sre.compile(
            # stdtag | < tagname ( \| [^<>] | stdtag )+ >
            r'''( <\w+(?:\~\w+)*> |
                < \w+ (?: \| (?: [^<>] | <\w+(?:\~\w+)*> )* )+ > )''', sre.X)):
            pieces = filter(None, tagre.split(pattern))
            self.replacers = map(FileFromPattern.PatternReplacer, pieces)

        def match(self, song):
            return ''.join([r.match(song) for r in self.replacers])

    class PatternReplacer(object):
        def __init__(self, pattern):
            if not (pattern.startswith('<') and pattern.endswith('>')):
                self.match = lambda song: pattern
            elif '|' not in pattern:
                self.match = lambda song: self.format(pattern[1:-1], song)
            else:
                parts = pattern[1:-1].split('|')
                check = parts.pop(0)
                parts.append('')
                if len(parts) > 3: # 1 or 2 real, 1 fallback; >2 real is bad
                    raise ValueError("pattern %s has extra sections" % pattern)
                r = map(FileFromPattern.Pattern, parts)
                self.match = lambda s: self.condmatch(check, r[0], r[1], s)

        def condmatch(self, check, true, false, song):
            if self.format(check, song): return true.match(song)
            else: return false.match(song)

        def format(self, tag, song):
            if tag.startswith('~') or not tag.replace('~','').isalnum():
                return tag.join('<>')

            fmt = FileFromPattern.format.get(tag, '%s')
            tag = FileFromPattern.override.get(tag, tag)

            if tag.startswith('~') or '~' not in tag:
                text = song.comma(tag)
                try: text = text.replace('/', '_')
                except AttributeError: pass
                try: return fmt % text
                except TypeError: return text
            else:
                fmtd = [self.format(t, song) for t in tag.split('~')]
                return ' - '.join(filter(None, fmtd))
