# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sre, stat, string, locale
from gettext import ngettext
N_ = str 

def to(string, frm="utf-8"):
    """Convert a string to the system encoding; used if you need to
    print to stdout. If you pass in a str (rather than a unicode) you
    should specify the encoding it's in with 'frm'."""
    enc = locale.getpreferredencoding()
    if isinstance(string, unicode): return string.encode(enc, "replace")
    else: return string.decode(frm).encode(enc, "replace")

def mtime(filename):
    """Return the mtime of a file, or 0 if an error occurs."""
    try: return os.path.getmtime(filename)
    except OSError: return 0

def mkdir(dir):
    """Make a directory, including all its parent directories. This does not
    raise an exception if the directory already exists (and is a
    directory)."""
    if not os.path.isdir(dir):
        os.makedirs(dir)

def escape(str):
    """Escape a string in a manner suitable for XML/Pango."""
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def unescape(str):
    """Unescape a string in a manner suitable for XML/Pango."""
    return str.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def re_esc(str):
    return "".join(map(
        lambda a: (a in "/.^$*+?{,}\\[]|()<>#=!:" and "\\" + a) or a, str))
sre.escape = re_esc

def parse_time(timestr):
    """Parse a time string in hh:mm:ss, mm:ss, or ss format."""
    try:
        return reduce(lambda s, a: s * 60 + int(a),
                      sre.split(":|\\.", timestr), 0)
    except (ValueError, sre.error):
        return 0

def format_rating(value):
    """Turn a number into a sequence of music notes."""
    return ('\xe2\x99\xaa' * int(value)).decode('utf-8')

def format_size(size):
    """Turn an integer size value into something human-readable."""
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
    """Turn a time value in seconds into hh:mm:ss or mm:ss."""
    if time > 3600: # 1 hour
        # time, in hours:minutes:seconds
        return "%d:%02d:%02d" % (time // 3600,
                                 (time % 3600) // 60, time % 60)
    else:
        # time, in minutes:seconds
        return "%d:%02d" % (time // 60, time % 60)

def format_time_long(time):
    """Turn a time value in seconds into x hours, x minutes, etc."""
    if time < 1: return _("No time information")
    cutoffs = [
        (60, N_("%d seconds"), N_("%d second")),
        (60, N_("%d minutes"), N_("%d minute")),
        (24, N_("%d hours"), N_("%d hour")),
        (365, N_("%d days"), N_("%d day")),
        (None, N_("%d years"), N_("%d year")),
    ]
    time_str = []
    for divisor, plural, single in cutoffs:
        if time < 1: break
        if divisor is None: time, unit = 0, time
        else: time, unit = divmod(time, divisor)
        if unit: time_str.append(ngettext(single, plural, unit) % unit)
    time_str.reverse()
    if len(time_str) > 2: time_str.pop()
    return ", ".join(time_str)

def fscoding():
    """Return the character set the filesystem uses."""
    if "CHARSET" in os.environ: return os.environ["CHARSET"]
    elif "G_BROKEN_FILENAMES" in os.environ:
        cset = os.environ.get("LC_CTYPE", "foo.utf-8")
        if "." in cset: return cset.split(".")[-1]
        else: return "utf-8"
    else: return "utf-8"

def fsdecode(s):
    """Decoding a string according to the filesystem encoding."""
    if isinstance(s, unicode): return s
    else: return decode(s, fscoding())

def fsencode(s):
    """Encode a string according to the filesystem encoding, replacing
    errors."""
    if isinstance(s, str): return s
    else: return s.encode(fscoding(), 'replace')

def decode(s, charset="utf-8"):
    """Decode a string; if an error occurs, replace characters and append
    a note to the string."""
    try: return s.decode(charset)
    except UnicodeError:
        return s.decode(charset, "replace") + " " + _("[Invalid Encoding]")

def encode(s, charset="utf-8"):
    """Encode a string; if an error occurs, replace characters and append
    a note to the string."""
    try: return s.encode(charset)
    # FIXME: Can *this* happen?
    except UnicodeError:
        return (s + " " + _("[Invalid Encoding]")).encode(charset, "replace")

def title(string):
    """Title-case a string using a less destructive method than str.title."""
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
    """True if 's' exists in the user's path, or is a fully-qualified
    existing path."""
    if s == "" or "/" in s:
        return os.path.exists(s)
    else:
        s = s.split()[0]
        for p in os.environ["PATH"].split(":"):
            p2 = os.path.join(p, s)
            if os.path.exists(p2): return True
        else: return False

def capitalize(str):
    """Capitalize a string, not affecting any character after the first."""
    return str[:1].upper() + str[1:]

# Split a string on ;s and ,s.
def split_value(s, splitters=",;&"):
    if not splitters: return [s.strip()]
    values = s.split("\n")
    for spl in splitters:
        new_values = []
        for v in values:
            new_values.extend(map(string.strip, v.split(spl)))
        values = new_values
    return values

def split_title(s, splitters=",;&"):
    title, subtitle = find_subtitle(s)
    if not subtitle: return (s, [])
    else: return (title.strip(), split_value(subtitle, splitters))

def split_people(s, splitters=",;&"):
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
    """Replace the user's home directory with ~/, if it appears at the
    start of the path name."""
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
    def __init__(self, pattern, filename=True):
        if filename and '/' in pattern and not pattern.startswith('/'):
            raise ValueError("Pattern %r is not rooted" % pattern)

        self.replacers = [self.Pattern(pattern, filename)]
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
        def __init__(self, pattern, filename=True, tagre=sre.compile(
            # stdtag | < tagname ( \| [^<>] | stdtag )+ >
            r'''( <\~?\w+(?:\~\w+)*> |
                < \w+ (?: \| (?: [^<>] | <\w+(?:\~\w+)*> )* )+ > )''', sre.X)):
            pieces = filter(None, tagre.split(pattern))
            self.replacers = [
                FileFromPattern.PatternReplacer(piece, filename=filename)
                for piece in pieces]

        def match(self, song):
            return ''.join([r.match(song) for r in self.replacers])

    class PatternReplacer(object):
        def __init__(self, pattern, filename=True):
            self.filename = filename
            if filename:
                self.__format = { 'tracknumber': '%02d', 'discnumber': '%d' }
                self.__override = {
                    'tracknumber': '~#track', 'discnumber': '~#disc' }
            else:
                self.__format = {}
                self.__override = {}

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
                r = [FileFromPattern.Pattern(p, filename) for p in parts]
                self.match = lambda s: self.condmatch(check, r[0], r[1], s)

        def condmatch(self, check, true, false, song):
            if check in song: return true.match(song)
            else: return false.match(song)

        def format(self, tag, song):
            if ((tag.startswith('~') or not tag.replace('~', '').isalnum())
                and (song(tag, None) is None)):
                return tag.join('<>')

            fmt = self.__format.get(tag, '%s')
            tag = self.__override.get(tag, tag)

            if tag.startswith('~') or '~' not in tag:
                text = song.comma(tag)
                if self.filename:
                    try: text = text.replace('/', '_')
                    except AttributeError: pass
                try: return fmt % text
                except TypeError: return text
            else:
                fmtd = [self.format(t, song) for t in tag.split('~')]
                return ' - '.join(filter(None, fmtd))

def website(site):
    site = site.replace("\\", "\\\\").replace("\"", "\\\"")
    for s in (["sensible-browser", "gnome-open"] +
              os.environ.get("BROWSER","").split(":")):
        if iscommand(s):
            if "%s" in s:
                s = s.replace("%s", '"' + site + '"')
                s = s.replace("%%", "%")
            else: s += " \"%s\"" % site
            if os.system(s + " &") == 0: return True
    else: return False
