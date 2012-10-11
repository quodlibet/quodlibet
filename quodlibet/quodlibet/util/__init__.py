# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011,2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import sys
import traceback
import urlparse
import unicodedata
import urllib

# title function was moved to a separate module
from quodlibet.util.titlecase import title

from quodlibet.const import FSCODING as fscoding, SUPPORT_EMAIL
from quodlibet.util.dprint import print_d, print_

if os.name == "nt":
    from win32com.shell import shellcon, shell

def strip_win32_incompat(string, BAD = '\:*?;"<>|'):
    """Strip Win32-incompatible characters.

    This only works correctly on Unicode strings.
    """
    new = u"".join(map(lambda s: (s in BAD and "_") or s, string))
    parts = new.split(os.sep)
    def fix_end(string):
        return re.sub(r'[\. ]$', "_", string)
    return unicode(os.sep).join(map(fix_end, parts))

def strip_win32_incompat_from_path(string):
    """Strip Win32-incompatible chars from a path, ignoring os.sep
    and the drive part"""
    drive, tail = os.path.splitdrive(string)
    tail = os.sep.join(map(strip_win32_incompat, tail.split(os.sep)))
    return drive + tail

def listdir(path, hidden=False):
    """List files in a directory, sorted, fully-qualified.

    If hidden is false, Unix-style hidden files are not returned.
    """
    path = fsnative(path)
    if hidden: filt = None
    else: filt = lambda base: not base.startswith(".")
    if path.endswith(os.sep): join = "".join
    else: join = os.sep.join
    return [join([path, basename])
            for basename in sorted(os.listdir(path))
            if filt(basename)]

class InstanceTracker(object):
    """A mixin for GObjects to return a list of all alive objects
    of a given type. Note that it must be used with a GObject or
    something with a connect method and destroy signal."""
    __kinds = {}

    def _register_instance(self, klass=None):
        """Register this object to be returned in the active instance list."""
        if klass is None: klass = type(self)
        self.__kinds.setdefault(klass, []).append(self)
        self.connect('destroy', self.__kinds[klass].remove)

    @classmethod
    def instances(klass):
        return klass.__kinds.get(klass, [])

class OptionParser(object):
    def __init__(self, name, version, description=None, usage=None):
        self.__name = name
        self.__version = version
        self.__args = {}
        self.__translate_short = {}
        self.__translate_long = {}
        self.__help = {}
        self.__usage = usage
        self.__description = description
        self.add(
            "help", shorts="h", help=_("Display brief usage information"))
        self.add(
            "version", shorts="v", help=_("Display version and copyright"))
        self.add("debug", shorts="d")

    def add(self, canon, help=None, arg="", shorts="", longs=[]):
        self.__args[canon] = arg
        for s in shorts: self.__translate_short[s] = canon
        for l in longs: self.__translate_long[l] = canon
        if help: self.__help[canon] = help

    def __shorts(self):
        shorts = ""
        for short, canon in self.__translate_short.items():
            shorts += short + (self.__args[canon] and "=" or "")
        return shorts

    def __longs(self):
        longs = []
        for long, arg in self.__args.items():
            longs.append(long + (arg and "=" or ""))
        for long, canon in self.__translate_long.items():
            longs.append(long + (self.__args[canon] and "=" or ""))
        return longs

    def __format_help(self, opt, space):
        if opt in self.__help:
            help = self.__help[opt]
            if self.__args[opt]:
                opt = "%s=%s" % (opt, self.__args[opt])
            return "  --%s %s\n" % (opt.ljust(space), help)

        else: return ""

    def help(self):
        l = 0
        for k in self.__help.keys():
            l = max(l, len(k) + len(self.__args.get(k, "")) + 4)

        s = _("Usage: %s %s\n") % (
                 sys.argv[0], self.__usage if self.__usage else _("[options]"))
        if self.__description:
            s += "%s - %s\n" % (self.__name, self.__description)
        s += "\n"
        keys = sorted(self.__help.keys())
        try: keys.remove("help")
        except ValueError: pass
        try: keys.remove("version")
        except ValueError: pass
        for h in keys: s += self.__format_help(h, l)
        if keys: s += "\n"
        s += self.__format_help("help", l)
        s += self.__format_help("version", l)
        return s

    def set_help(self, newhelp):
        self.__help = newhelp

    def version(self):
        return _("""\
{title} {version}
<{email}>
Copyright {dates}\t{authors}

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
""").format(title=self.__name,  version=self.__version, dates="2004-2012",
        email=SUPPORT_EMAIL,
        authors="Joe Wreschnig, Michael Urman, Iñigo Serna,\n\t\t\t"
                "Steven Robertson, Christoph Reiter, Nick Boultbee and others.")

    def parse(self, args=None):
        if args is None: args = sys.argv[1:]
        from getopt import getopt, GetoptError
        try: opts, args = getopt(args, self.__shorts(), self.__longs())
        except GetoptError, s:
            s = str(s)
            text = []
            if "not recognized" in s:
                text.append(
                    _("Option %r not recognized.") % s.split()[1])
            elif "requires argument" in s:
                text.append(
                    _("Option %r requires an argument.") % s.split()[1])
            elif "unique prefix" in s:
                text.append(
                    _("%r is not a unique prefix.") % s.split()[1])
            if "help" in self.__args:
                text.append(_("Try %s --help.") % sys.argv[0])

            print_e("\n".join(text))
            raise SystemExit(True)
        else:
            transopts = {}
            for o, a in opts:
                if o.startswith("--"):
                    o = self.__translate_long.get(o[2:], o[2:])
                elif o.startswith("-"):
                    o = self.__translate_short.get(o[1:], o[1:])
                if o == "help":
                    print_(self.help())
                    raise SystemExit
                elif o == "version":
                    print_(self.version())
                    raise SystemExit
                elif o == "debug":
                    from quodlibet import const
                    const.DEBUG = True
                if self.__args[o]: transopts[o] = a
                else: transopts[o] = True

            return transopts, args

def mtime(filename):
    """Return the mtime of a file, or 0 if an error occurs."""
    try: return os.path.getmtime(filename)
    except OSError: return 0

def size(filename):
    """Return the size of a file, or 0 if an error occurs."""
    try: return os.path.getsize(filename)
    except OSError: return 0

def mkdir(dir, *args):
    """Make a directory, including all its parent directories. This does not
    raise an exception if the directory already exists (and is a
    directory)."""
    if not os.path.isdir(dir):
        os.makedirs(dir, *args)

def escape(str):
    """Escape a string in a manner suitable for XML/Pango."""
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def unescape(str):
    """Unescape a string in a manner suitable for XML/Pango."""
    return str.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def escape_filename(s):
    """Escape a string in a manner suitable for a filename."""
    if isinstance(s, unicode):
        s = s.encode("utf-8")
    return urllib.quote(s, safe="").decode("utf-8")

def unescape_filename(s):
    """Unescape a string in a manner suitable for a filename."""
    if isinstance(s, unicode):
        s = s.encode("utf-8")
    return urllib.unquote(s).decode("utf-8")

def parse_time(timestr, err=(ValueError, re.error)):
    """Parse a time string in hh:mm:ss, mm:ss, or ss format."""
    if timestr[0:1] == "-":
        m = -1
        timestr = timestr[1:]
    else: m = 1
    try:
        return m * reduce(lambda s, a: s * 60 + int(a),
                          re.split(r":|\.", timestr), 0)
    except err: return 0

RATING_PRECISION = 0.25
RATING_SYMBOL = u'\u266a'
def format_rating(value):
    """Turn a number into a sequence of music notes."""
    return RATING_SYMBOL * int(round((1/RATING_PRECISION) * min(value, 1.0)))

def format_size(size):
    """Turn an integer size value into something human-readable."""
    # TODO: Better i18n of this (eg use O/KO/MO/GO in French)
    if size >= 1024*1024*1024:
        return "%.1f GB" % (float(size) / (1024*1024*1024))
    elif size >= 1024*1024 * 100:
        return "%.0f MB" % (float(size) / (1024*1024))
    elif size >= 1024*1024 * 10:
        return "%.1f MB" % (float(size) / (1024*1024))
    elif size >= 1024*1024:
        return "%.2f MB" % (float(size) / (1024*1024))
    elif size >= 1024 * 10:
        return "%d KB" % int(size / 1024)
    elif size >= 1024:
        return "%.2f KB" % (float(size) / 1024)
    else:
        return "%d B" % size

def format_time(time):
    """Turn a time value in seconds into hh:mm:ss or mm:ss."""
    if time < 0:
        time = abs(time)
        prefix = "-"
    else: prefix = ""
    if time >= 3600: # 1 hour
        # time, in hours:minutes:seconds
        return "%s%d:%02d:%02d" % (prefix, time // 3600,
                                   (time % 3600) // 60, time % 60)
    else:
        # time, in minutes:seconds
        return "%s%d:%02d" % (prefix, time // 60, time % 60)

def format_time_long(time):
    """Turn a time value in seconds into x hours, x minutes, etc."""
    if time < 1: return _("No time information")
    cutoffs = [
        (60, "%d seconds", "%d second"),
        (60, "%d minutes", "%d minute"),
        (24, "%d hours", "%d hour"),
        (365, "%d days", "%d day"),
        (None, "%d years", "%d year"),
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

def fsdecode(s, note=True):
    """Decoding a string according to the filesystem encoding.
    note specifies whether a note should be appended if decoding failed."""
    if isinstance(s, unicode): return s
    elif note:
        return decode(s, fscoding)
    else:
        return s.decode(fscoding, 'replace')

def fsencode(s, note=False):
    """Encode a string according to the filesystem encoding.
    note specifies whether a note should be appended if encoding failed."""
    if isinstance(s, str): return s
    elif note:
        return encode(s, fscoding)
    else:
        return s.encode(fscoding, 'replace')

"""
Path related functions like open, os.listdir have different behavior on win32

- Passing a string calls the old non unicode win API.
  In case of listdir this leads to "?" for >1byte chars and to
  1 byte chars encoded using the fs encoding. -> DO NOT USE!

- Passing a unicode object internally calls the windows unicode functions.
  This will mostly lead to proper unicode paths (except expanduser).

  And that's why QL is using unicode paths on win and encoded paths
  everywhere else.
"""

if sys.platform == "win32":
    fsnative = fsdecode # Decode a filename on windows
else:
    fsnative = fsencode # Encode it on other platforms

def split_scan_dirs(s):
    """Split the value of the "scan" setting, accounting for drive letters on
    win32."""
    if sys.platform == "win32":
        return filter(None, re.findall(r"[a-zA-Z]:[\\/][^:]*", s))
    else:
        return filter(None, s.split(":"))

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
    except UnicodeError:
        return (s + " " + _("[Invalid Encoding]")).encode(charset, "replace")

def iscommand(s):
    """True if an executable file 's' exists in the user's path, or is a
    fully-qualified existing executable file."""

    if s == "" or os.path.sep in s:
        return os.path.isfile(s) and os.access(s, os.X_OK)
    else:
        s = s.split()[0]
        for p in os.defpath.split(os.path.pathsep):
            p2 = os.path.join(p, s)
            if os.path.isfile(p2) and os.access(p2, os.X_OK):
                return True
        else: return False

def capitalize(str):
    """Capitalize a string, not affecting any character after the first."""
    return str[:1].upper() + str[1:]

def split_value(s, splitters=["/", "&", ","]):
    """Splits a string. The first match in 'splitters' is used as the
    separator; subsequent matches are intentionally ignored."""
    if not splitters: return [s.strip()]
    values = s.split("\n")
    for spl in splitters:
        spl = re.compile(r"\b\s*%s\s*\b" % re.escape(spl), re.UNICODE)
        if not filter(spl.search, values): continue
        new_values = []
        for v in values:
            new_values.extend([st.strip() for st in spl.split(v)])
        return new_values
    return values

def split_title(s, splitters=["/", "&", ","]):
    title, subtitle = find_subtitle(s)
    return ((title.strip(), split_value(subtitle, splitters))
            if subtitle else (s, []))


__FEATURING = ["feat.", "featuring", "feat", "ft", "ft.", "with", "w/"]
__ORIGINALLY = ["originally by ", " cover"]
# Cache case-insensitive regex searches of the above
__FEAT_REGEX = [re.compile(re.escape(s + " "), re.I) for s in __FEATURING]
__ORIG_REGEX = [re.compile(re.escape(s), re.I) for s in __ORIGINALLY]

def split_people(s, splitters=["/", "&", ","]):
    title, subtitle = find_subtitle(s)
    if not subtitle:
        parts = s.split(" ")
        if len(parts) > 2:
            for feat in __FEATURING:
                try:
                    i = [p.lower() for p in parts].index(feat)
                    orig = " ".join(parts[:i])
                    others = " ".join(parts[i+1:])
                    return (orig, split_value(others, splitters))
                except (ValueError, IndexError): pass
        return (s, [])
    else:
        old = subtitle
        # TODO: allow multiple substitutions across types, maybe
        for regex in (__FEAT_REGEX + __ORIG_REGEX):
            subtitle = re.sub(regex, "", subtitle, 1)
            if old != subtitle:
                # Only change once
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

def split_numeric(s, limit=10,
        reg=re.compile(r"[0-9][0-9]*\.?[0-9]*").search,
        join=u" ".join):
    """Separate numeric values from the string and convert to float, so
    it can be used for human sorting. Also removes all extra whitespace."""
    result = reg(s)
    if not result or not limit:
        return (join(s.split()),)
    else:
        start, end = result.span()
        return (
            join(s[:start].split()),
            float(result.group()),
            split_numeric(s[end:], limit - 1))

def human_sort_key(s, normalize=unicodedata.normalize):
    if not isinstance(s, unicode):
        s = s.decode("utf-8")
    s = normalize("NFD", s.lower())
    return s and split_numeric(s)

def find_subtitle(title):
    if isinstance(title, str): title = title.decode('utf-8', 'replace')
    for pair in [u"[]", u"()", u"~~", u"--", u"\u301c\u301c", u'\uff08\uff09']:
        if pair[0] in title[:-1] and title.endswith(pair[1]):
            r = len(pair[1])
            l = title[0:-r].rindex(pair[0])
            if l != 0:
                subtitle = title[l+len(pair[0]):-r]
                title = title[:l]
                return title.rstrip(), subtitle
    else: return title, None

def expanduser(filename):
    """needed because expanduser does not return wide character paths
    on windows even if a unicode path gets passed."""
    if os.name == "nt":
        profile = shell.SHGetFolderPath(0, shellcon.CSIDL_PROFILE, 0, 0)
        if filename == "~": return profile
        if filename.startswith(u"~" + os.path.sep):
            return os.path.join(profile, filename[2:])
    return os.path.expanduser(filename)

def unexpand(filename, HOME=expanduser("~")):
    """Replace the user's home directory with ~/, if it appears at the
    start of the path name."""
    sub = (os.name == "nt" and "%USERPROFILE%") or "~"
    if filename == HOME: return sub
    elif filename.startswith(HOME + os.path.sep):
        filename = filename.replace(HOME, sub, 1)
    return filename

def website(site):
    site = site.replace("\\", "\\\\").replace("\"", "\\\"")
    for prog in (["gnome-open", "xdg-open", "sensible-browser"] +
              os.environ.get("BROWSER","").split(":")):
        if iscommand(prog):
            args = prog.split()
            for i, arg in enumerate(args):
                if arg == "%s":
                    args[i] = site
                    break
            else: args.append(site)
            try: spawn(args)
            except RuntimeError: return False
            else: return True
    else: return False

def tag(name, cap=True):
    # Return a 'natural' version of the tag for human-readable bits.
    # Strips ~ and ~# from the start and runs it through a map (which
    # the user can configure).
    if not name: return _("Invalid tag")
    else:
        from quodlibet.util.tags import readable
        parts = map(readable, tagsplit(name))
        if cap:
            # Translators: If tag names, when capitalized, should not
            # be title-cased ("Looks Like This"), but rather only have
            # the first letter capitalized, translate this string as
            # something other than "check|titlecase?".
            if _("check|titlecase?") == "check|titlecase?":
                parts = map(title, parts)
            else:
                parts = map(capitalize, parts)
        return " / ".join(parts)

def tagsplit(tag):
    """Split a (potentially) tied tag into a list of atomic tags. Two ~~s
    make the next tag prefixed with a ~, so ~foo~~bar => [foo, ~bar]."""
    if "~" in tag[1:]:
        if tag.startswith("~") and not tag.startswith("~#"): tag = tag[1:]
        tags = []
        front = ""
        for part in tag.split("~"):
            if part:
                tags.append(front + part)
                front = ""
            else: front = "~"
        return tags
    else: return [tag]

def pattern(pat, cap=True, esc=False):
    """Return a 'natural' version of the pattern string for human-readable
    bits. Assumes all tags in the pattern are present."""
    from quodlibet.parse import Pattern, XMLFromPattern
    class Fakesong(dict):
        cap = False
        def comma(self, key):
            return " - ".join(self.list(key))
        def list(self, key):
            return [tag(k, self.cap) for k in tagsplit(key)]
        list_seperate = list
        __call__ = comma

    fakesong = Fakesong({'filename': tag('filename', cap)})
    fakesong.cap = cap
    try:
        p = (esc and XMLFromPattern(pat)) or Pattern(pat)
    except ValueError:
        return _("Invalid pattern")

    return p.format(fakesong)

def spawn(argv, stdout=False):
    """Asynchronously run a program. argv[0] is the executable name, which
    must be fully qualified or in the path. If stdout is True, return
    a file object corresponding to the child's standard output; otherwise,
    return the child's process ID.

    argv must be strictly str objects to avoid encoding confusion.
    """

    import gobject
    types = map(type, argv)
    if not (min(types) == max(types) == str):
        raise TypeError("executables and arguments must be str objects")
    print_d("Running %r" % " ".join(argv))
    args = gobject.spawn_async(
        argv, flags=gobject.SPAWN_SEARCH_PATH, standard_output=stdout)
    if stdout: return os.fdopen(args[2])
    else: return args[0]

def fver(tup):
    return ".".join(map(str, tup))

def uri_is_valid(uri):
    return bool(urlparse.urlparse(uri)[0])

def make_case_insensitive(filename):
    return "".join(["[%s%s]" % (c.lower(), c.upper()) for c in filename])

def print_exc(limit=None, file=None):
    """A wrapper preventing crashes on broken pipes in print_exc."""
    if not file: file = sys.stderr
    print_(traceback.format_exc(limit=limit), output=file)

class DeferredSignal(object):
    """A wrapper for connecting functions to signals.

    Some signals may fire hundreds of times, but only require processing
    once per group. This class pushes the call to the mainloop at idle
    priority and prevents multiple calls from being inserted in the
    mainloop at a time, greatly improving responsiveness in some places.

    Example usage:

    def func(widget, user_arg):
        pass
    widget.connect('signal', DeferredSignal(func), user_arg)
    """

    import gobject
    __slots__ = ['func', 'dirty']
    def __init__(self, func):
        self.func = func
        self.dirty = False

    def __call__(self, *args):
        if not self.dirty:
            self.dirty = True
            self.gobject.idle_add(self._wrap, *args)

    def _wrap(self, *args):
        self.func(*args)
        self.dirty = False

def gobject_weak(fun, *args, **kwargs):
    """Connect to a signal and disconnect if destroy gets emitted.
    If parent is given, it connects to its destroy signal
    Example:
        gobject_weak(gobject_1.connect, 'changed', self.__changed)
        gobject_weak(gobject_1.connect, 'changed', self.__changed,
            parent=gobject_2)
    """
    parent = kwargs.pop("parent", None)
    obj = fun.__self__
    sig = fun(*args)
    disconnect = lambda obj, handle: obj.disconnect(handle)
    if parent: parent.connect_object('destroy', disconnect, obj, sig)
    else: obj.connect('destroy', disconnect, sig)
    return sig

class cached_property(object):
    """A read-only @property that is only evaluated once."""
    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result

def xdg_get_system_data_dirs():
    """http://standards.freedesktop.org/basedir-spec/latest/"""
    data_dirs = os.getenv("XDG_DATA_DIRS")
    if data_dirs:
        return map(os.path.abspath, data_dirs.split(":"))
    else:
        return ("/usr/local/share/", "/usr/share/")

def xdg_get_cache_home():
    data_home = os.getenv("XDG_CACHE_HOME")
    if data_home:
        return os.path.abspath(data_home)
    else:
        return os.path.join(os.path.expanduser("~"), ".cache")

def xdg_get_data_home():
    data_home = os.getenv("XDG_DATA_HOME")
    if data_home:
        return os.path.abspath(data_home)
    else:
        return os.path.join(os.path.expanduser("~"), ".local", "share")

def find_mount_point(path):
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path

def pathname2url_win32(path):
    # stdlib version raises IOError for more than one ':' which can appear
    # using a virtual box shared folder and it inserts /// at the beginning
    # but it should be /.
    quote = urllib.quote
    if path[1:2] != ":" or path[:1] == "\\":
        if path[:2] == "\\\\":
            path = path[2:]
        return quote("/".join(path.split("\\")))
    drive, remain = path.split(":", 1)
    return "/%s:%s" % (quote(drive), quote("/".join(remain.split("\\"))))

if os.name == "nt":
    pathname2url = pathname2url_win32
else:
    pathname2url = urllib.pathname2url


# See http://stackoverflow.com/questions/1151658/python-hashable-dicts
class HashableDict(dict):
    """Standard dict, made hashable. Useful for making sets of dicts etc"""
    def __key(self):
        return tuple((k,self[k]) for k in sorted(self))
    def __hash__(self):
        return hash(self.__key())
    def __eq__(self, other):
        return self.__key() == other.__key()


def sanitize_tags(tags, stream=False):
    """Returns a new sanitized tag dict. stream defines if the
    tags of a main/base song should be changed or of a stream song.
    e.g. title will be removed for the base song but not for the stream one.
    """

    san = {}
    for key, value in tags.iteritems():
        key = key.lower()
        key = {"location": "website"}.get(key, key)

        if isinstance(value, unicode):
            lower = value.lower().strip()

            if key == "channel-mode":
                if "stereo" in lower or "dual" in lower:
                    value = u"stereo"
            elif key == "audio-codec":
                if "mp3" in lower:
                    value = u"MP3"
                elif "aac" in lower or "advanced" in lower:
                    value = u"MPEG-4 AAC"
                elif "vorbis" in lower:
                    value = u"Ogg Vorbis"

            if lower in ("http://www.shoutcast.com", "http://localhost/",
                "default genre", "none", "http://", "unnamed server",
                "unspecified", "n/a"):
                continue

        if key == "duration":
            try: value = int(long(value) / 1000)
            except ValueError: pass
            else:
                if not stream: continue
                key = "~#length"
        elif key == "bitrate":
            try: value = int(value) / 1000
            except ValueError: pass
            else:
                if not stream: continue
                key = "~#bitrate"
        elif key == "nominal-bitrate":
            try: value = int(value) / 1000
            except ValueError: pass
            else:
                if stream: continue
                key = "~#bitrate"

        if key in ("emphasis", "mode", "layer", "maximum-bitrate",
            "minimum-bitrate", "has-crc", "homepage"):
            continue

        if not stream and key in ("title", "album", "artist", "date"):
            continue

        if isinstance(value, (int, long, float)):
            if not key.startswith("~#"):
                key = "~#" + key
            san[key] = value
        else:
            if key.startswith("~#"):
                key = key[2:]

            if not isinstance(value, unicode):
                continue

            value = value.strip()
            if key in san:
                if value not in san[key].split("\n"):
                    san[key] += "\n" + value
            else:
                san[key] = value

    return san


def build_filter_query(key, values):
    """Create a text query that matches a union of all values for a key

    build_filter_query("foo", ["x", "y"])
    => foo = |("x"c, "y"c)
    build_filter_query("~#foo", ["1"])
    => #(foo = 1)
    """

    if not values:
        return u""
    if key.startswith("~#"):
        nheader = key[2:]
        queries = ["#(%s = %s)" % (nheader, i) for i in values]
        if len(queries) > 1:
            return u"|(%s)" % ", ".join(queries)
        else:
            return queries[0]
    else:
        text = ", ".join(
            ["'%s'c" % v.replace("\\", "\\\\").replace("'", "\\'")
             for v in values])
        if len(values) == 1:
            return u"%s = %s" % (key, text)
        else:
            return u"%s = |(%s)" % (key, text)
