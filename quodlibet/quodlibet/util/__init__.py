# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011,2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import random
import re
import sys
import traceback
import urlparse
import unicodedata
import subprocess
import webbrowser

from quodlibet.util.path import (fsdecode, fsencode, iscommand, fsnative,
    expanduser, pathname2url, strip_win32_incompat)
from quodlibet.util.string.splitters import split_value
from quodlibet.util.titlecase import title

from quodlibet.const import FSCODING as fscoding, SUPPORT_EMAIL, COPYRIGHT
from quodlibet import config
from quodlibet.util.dprint import print_d, print_


class InstanceTracker(object):
    """A mixin for GObjects to return a list of all alive objects
    of a given type. Note that it must be used with a GObject or
    something with a connect method and destroy signal."""
    __kinds = {}

    def _register_instance(self, klass=None):
        """Register this object to be returned in the active instance list."""
        if klass is None:
            klass = type(self)
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
        for s in shorts:
            self.__translate_short[s] = canon
        for l in longs:
            self.__translate_long[l] = canon
        if help:
            self.__help[canon] = help

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
        else:
            return ""

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
        try:
            keys.remove("help")
        except ValueError:
            pass
        try:
            keys.remove("version")
        except ValueError:
            pass
        for h in keys:
            s += self.__format_help(h, l)
        if keys:
            s += "\n"
        s += self.__format_help("help", l)
        s += self.__format_help("version", l)
        return s

    def set_help(self, newhelp):
        self.__help = newhelp

    def version(self):
        return ("""\
{title} {version}
<{email}>
{copyright}\
""").format(title=self.__name, version=self.__version, dates="2004-2012",
            email=SUPPORT_EMAIL, copyright=COPYRIGHT)

    def parse(self, args=None):
        if args is None:
            args = sys.argv[1:]
        from getopt import getopt, GetoptError
        try:
            opts, args = getopt(args, self.__shorts(), self.__longs())
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
                if self.__args[o]:
                    transopts[o] = a
                else:
                    transopts[o] = True

            return transopts, args


def escape(str):
    """Escape a string in a manner suitable for XML/Pango."""
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def unescape(str):
    """Unescape a string in a manner suitable for XML/Pango."""
    return str.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def parse_time(timestr, err=(ValueError, re.error)):
    """Parse a time string in hh:mm:ss, mm:ss, or ss format."""
    if timestr[0:1] == "-":
        m = -1
        timestr = timestr[1:]
    else:
        m = 1
    try:
        return m * reduce(lambda s, a: s * 60 + int(a),
                          re.split(r":|\.", timestr), 0)
    except err:
        return 0


def format_rating(value, blank=True):
    """Turn a number into a sequence of rating symbols."""
    prefs = config.RATINGS
    steps = prefs.number
    value = max(min(value, 1.0), 0)
    ons = int(round(steps * value))
    offs = (steps - ons) if blank else 0
    return prefs.full_symbol * ons + prefs.blank_symbol * offs


def format_size(size):
    """Turn an integer size value into something human-readable."""
    # TODO: Better i18n of this (eg use O/KO/MO/GO in French)
    if size >= 1024 ** 3:
        return "%.1f GB" % (float(size) / (1024 ** 3))
    elif size >= 1024 ** 2 * 100:
        return "%.0f MB" % (float(size) / (1024 ** 2))
    elif size >= 1024 ** 2 * 10:
        return "%.1f MB" % (float(size) / (1024 ** 2))
    elif size >= 1024 ** 2:
        return "%.2f MB" % (float(size) / (1024 ** 2))
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
    else:
        prefix = ""
    if time >= 3600:  # 1 hour
        # time, in hours:minutes:seconds
        return "%s%d:%02d:%02d" % (prefix, time // 3600,
                                   (time % 3600) // 60, time % 60)
    else:
        # time, in minutes:seconds
        return "%s%d:%02d" % (prefix, time // 60, time % 60)


def format_time_long(time, limit=2):
    """Turn a time value in seconds into x hours, x minutes, etc.

    `limit` limits the count of units used, so the result will be <= time.
    0 means no limit.
    """

    if time < 1:
        return _("No time information")

    cutoffs = [
        (60, "%d seconds", "%d second"),
        (60, "%d minutes", "%d minute"),
        (24, "%d hours", "%d hour"),
        (365, "%d days", "%d day"),
        (None, "%d years", "%d year"),
    ]

    time_str = []
    for divisor, plural, single in cutoffs:
        if time < 1:
            break
        if divisor is None:
            time, unit = 0, time
        else:
            time, unit = divmod(time, divisor)
        if unit:
            time_str.append(ngettext(single, plural, unit) % unit)
    time_str.reverse()

    if limit:
        time_str = time_str[:limit]

    return ", ".join(time_str)


def split_scan_dirs(s):
    """Split the value of the "scan" setting, accounting for drive letters on
    win32."""
    if sys.platform == "win32":
        return filter(None, re.findall(r"[a-zA-Z]:[\\/][^:]*", s))
    else:
        return filter(None, s.split(":"))


def capitalize(str):
    """Capitalize a string, not affecting any character after the first."""
    return str[:1].upper() + str[1:]


def _split_numeric_sortkey(s, limit=10,
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
            _split_numeric_sortkey(s[end:], limit - 1))


def human_sort_key(s, normalize=unicodedata.normalize):
    if not isinstance(s, unicode):
        s = s.decode("utf-8")
    s = normalize("NFD", s.lower())
    return s and _split_numeric_sortkey(s)


def website(site):
    """Open the given URL in the user's default browser"""

    if os.name == "nt":
        return webbrowser.open(site)

    # all commands here return immediately
    for prog in ["xdg-open", "gnome-open"]:
        if not iscommand(prog):
            continue

        status = subprocess.check_call([prog, site])
        if status == 0:
            return True

    # sensible-browser is a debian thing
    blocking_progs = ["sensible-browser"]
    blocking_progs.extend(os.environ.get("BROWSER", "").split(":"))

    for prog in blocking_progs:
        if not iscommand(prog):
            continue

        # replace %s with the url
        args = prog.split()
        for i, arg in enumerate(args):
            if arg == "%s":
                args[i] = site
                break
        else:
            args.append(site)

        # calling e.g. firefox blocks, so call async and hope for the best
        try:
            spawn(args)
        except RuntimeError:
            continue
        else:
            return True

    return False


def tag(name, cap=True):
    # Return a 'natural' version of the tag for human-readable bits.
    # Strips ~ and ~# from the start and runs it through a map (which
    # the user can configure).
    if not name:
        return _("Invalid tag")
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
        if tag.startswith("~") and not tag.startswith("~#"):
            tag = tag[1:]
        tags = []
        front = ""
        for part in tag.split("~"):
            if part:
                tags.append(front + part)
                front = ""
            else:
                front = "~"
        return tags
    else:
        return [tag]


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

    from gi.repository import GLib

    types = map(type, argv)
    if not (min(types) == max(types) == str):
        raise TypeError("executables and arguments must be str objects")
    print_d("Running %r" % " ".join(argv))
    args = GLib.spawn_async(argv=argv, flags=GLib.SpawnFlags.SEARCH_PATH,
                            standard_output=stdout)

    if stdout:
        return os.fdopen(args[2])
    else:
        return args[0]


def fver(tup):
    return ".".join(map(str, tup))


def uri_is_valid(uri):
    return bool(urlparse.urlparse(uri)[0])


def make_case_insensitive(filename):
    return "".join(["[%s%s]" % (c.lower(), c.upper()) for c in filename])


def print_exc(limit=None, file=None):
    """A wrapper preventing crashes on broken pipes in print_exc."""
    if not file:
        file = sys.stderr
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

    __slots__ = ['func', 'dirty']

    def __init__(self, func):
        self.func = func
        self.dirty = False

    def __call__(self, *args):
        if not self.dirty:
            self.dirty = True
            from gi.repository import GLib
            GLib.idle_add(self._wrap, *args)

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
    if parent:
        parent.connect_object('destroy', disconnect, obj, sig)
    else:
        obj.connect('destroy', disconnect, sig)
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
            try:
                value = int(long(value) / 1000)
            except ValueError:
                pass
            else:
                if not stream:
                    continue
                key = "~#length"
        elif key == "bitrate":
            try:
                value = int(value) / 1000
            except ValueError:
                pass
            else:
                if not stream:
                    continue
                key = "~#bitrate"
        elif key == "nominal-bitrate":
            try:
                value = int(value) / 1000
            except ValueError:
                pass
            else:
                if stream:
                    continue
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


def limit_songs(songs, max, weight_by_ratings=False):
    """Choose at most `max` songs from `songs`,
    optionally giving weighting to ~#rating"""

    if not max or len(songs) < max:
        return songs
    else:
        if weight_by_ratings:
            def choose(r1, r2):
                if r1 or r2:
                    return cmp(random.random(), r1 / (r1 + r2))
                else:
                    return random.randint(-1, 1)

            def rating(song):
                return song("~#rating")
            songs.sort(cmp=choose, key=rating)
        else:
            random.shuffle(songs)
        return songs[:max]


def gi_require_versions(name, versions):
    """Like gi.require_version, but will take a list of versions.

    Returns the required version or raises ValueError.
    """

    assert versions

    import gi

    for version in versions:
        try:
            gi.require_version(name, version)
        except ValueError as e:
            pass
        else:
            return version
    else:
        raise e
