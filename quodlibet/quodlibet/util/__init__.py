# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
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

from quodlibet.const import FSCODING as fscoding, ENCODING

def strip_win32_incompat(string, BAD = '\:*?;"<>|'):
    """Strip Win32-incompatible characters.

    This only works correctly on Unicode strings.
    """
    new = u"".join(map(lambda s: (s in BAD and "_") or s, string))
    parts = new.split(os.sep)
    def fix_end(string):
        return re.sub(r'[\. ]$', "_", string)
    return unicode(os.sep).join(map(fix_end, parts))

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

    def instances(klass): return klass.__kinds.get(klass, [])
    instances = classmethod(instances)

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

        if self.__usage: s = _("Usage: %s %s") % (sys.argv[0], self.__usage)
        else: s = _("Usage: %s %s") % (sys.argv[0], _("[options]"))
        s += "\n"
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
%s %s - <quod-libet-development@googlegroups.com>
Copyright 2004-2005 Joe Wreschnig, Michael Urman, and others

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
""") % (self.__name, self.__version)

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
def format_rating(value):
    """Turn a number into a sequence of music notes."""
    return (u'\u266a' * int(round((1/RATING_PRECISION) * value)))

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

def fsdecode(s):
    """Decoding a string according to the filesystem encoding."""
    if isinstance(s, unicode): return s
    else: return decode(s, fscoding)

def fsencode(s):
    """Encode a string according to the filesystem encoding, replacing
    errors."""
    if isinstance(s, str): return s
    else: return s.encode(fscoding, 'replace')

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
        return (os.path.isfile(s) and os.access(s, os.X_OK))
    else:
        s = s.split()[0]
        for p in os.defpath.split(os.path.pathsep):
            p2 = os.path.join(p, s)
            if (os.path.isfile(p2) and os.access(p2, os.X_OK)):
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
    if not subtitle: return (s, [])
    else: return (title.strip(), split_value(subtitle, splitters))

def split_people(s, splitters=["/", "&", ","]):
    FEATURING = ["feat.", "featuring", "feat", "ft", "ft.", "with", "w/"]

    title, subtitle = find_subtitle(s)
    if not subtitle:
        parts = s.split(" ")
        if len(parts) > 2:
            for feat in FEATURING:
                try:
                    i = [p.lower() for p in parts].index(feat)
                    orig = " ".join(parts[:i])
                    others = " ".join(parts[i+1:])
                    return (orig, split_value(others, splitters))
                except (ValueError, IndexError): pass
        return (s, [])
    else:
        for feat in FEATURING:
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

def split_numeric(s, reg=re.compile(r"([0-9]+\.?[0-9]*)")):
    """Seperate numeric values from the string and convert to float, so
    it can be used for human sorting. Also removes all extra whitespace."""
    if not s: return ('',)
    result = reg.search(s)
    if not result: return (u" ".join(s.split()),)
    else:
        first = u" ".join(s[:result.start()].split())
        last = s[result.end():].strip()
        return (first, float(result.group(0)), split_numeric(last))

def human_sort_key(s):
    if not isinstance(s, unicode):
        s = s.decode("utf-8")
    s = unicodedata.normalize('NFD', s.lower())
    return split_numeric(s[:1024])

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

def unexpand(filename, HOME=os.path.expanduser("~")):
    """Replace the user's home directory with ~/, if it appears at the
    start of the path name."""
    if filename == HOME: return "~"
    elif filename.startswith(HOME + "/"):
        filename = filename.replace(HOME, "~", 1)
    return filename

def website(site):
    site = site.replace("\\", "\\\\").replace("\"", "\\\"")
    for prog in (["xdg-open", "gnome-open", "sensible-browser"] +
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
    p = (esc and XMLFromPattern(pat)) or Pattern(pat)
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
        return data_dirs.split(":")
    else:
        return ("/usr/local/share/", "/usr/share/")
