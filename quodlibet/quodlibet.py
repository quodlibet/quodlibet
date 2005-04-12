#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
# <quodlibet@lists.sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

import os, sys

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
        for l in longs: self.__translate_longs[s] = canon
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
        else: s = _("Usage: %s [options]") % sys.argv[0]
        s += "\n"
        if self.__description:
            s += "%s - %s\n" % (self.__name, self.__description)
        s += "\n"
        keys = self.__help.keys()
        keys.sort()
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
%s %s - <quodlibet@lists.sacredchao.net>
Copyright 2004-2005 Joe Wreschnig, Michael Urman, and others

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
""") % (self.__name, self.__version)

    def parse(self, args=None):
        from util import to
        if args is None: args = sys.argv[1:]
        from getopt import getopt, GetoptError
        try: opts, args = getopt(args, self.__shorts(), self.__longs())
        except GetoptError, s:
            s = str(s)
            text = []
            if "not recognized" in s:
                text.append(
                    _("E: Option '%s' not recognized.") % s.split()[1])
            elif "requires argument" in s:
                text.append(
                    _("E: Option '%s' requires an argument.") % s.split()[1])
            elif "unique prefix" in s:
                text.append(
                    _("E: '%s' is not a unique prefix.") % s.split()[1])
            if "help" in self.__args:
                text.append(_("E: Try %s --help.") % sys.argv[0])

            raise SystemExit(to("\n".join(text)))
        else:
            transopts = {}
            for o, a in opts:
                if o.startswith("--"):
                    o = self.__translate_long.get(o[2:], o[2:])
                elif o.startswith("-"):
                    o = self.__translate_short.get(o[1:], o[1:])
                if o == "help":
                    print self.help()
                    raise SystemExit
                elif o == "version":
                    print self.version()
                    raise SystemExit
                if self.__args[o]: transopts[o] = a
                else: transopts[o] = True

            return transopts, args

def main():
    import signal, gtk, widgets
    gtk.threads_init()

    SIGNALS = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]

    window = widgets.init()

    from threading import Thread
    t = Thread(target=player.playlist.play, args=(widgets.widgets.watcher,))
    for sig in SIGNALS: signal.signal(sig, gtk.main_quit)
    enable_periodic_save()
    gtk.quit_add(0, save_and_quit, t)
    gtk.threads_enter()
    t.start()
    gtk.main()
    gtk.threads_leave()

def print_status():
    if not os.path.exists(const.CURRENT): print "stopped"
    elif os.path.exists(const.PAUSED): print "paused"
    else: print "playing"
    raise SystemExit

def save_and_quit(thread):
    player.playlist.quitting()
    thread.join()
    print to(_("Saving song library."))
    library.save(const.LIBRARY)
    config.write(const.CONFIG)
    cleanup()
    raise SystemExit

def refresh_cache():
    if isrunning():
        raise SystemExit(to(_(
            "The library cannot be refreshed while Quod Libet is running.")))
    import library, config, const
    config.init(const.CONFIG)
    library.init()
    print to(_("Loading, scanning, and saving your library."))
    library.library.load(const.LIBRARY)
    for x, y in library.library.rebuild(): pass
    library.library.save(const.LIBRARY)
    raise SystemExit

def print_playing(fstring = "<artist~album~tracknumber~title>"):
    import util; from util import to, FileFromPattern
    from formats.audio import AudioFile
    try:
        fn = file(const.CURRENT)
        data = {}
        for line in fn:
            line = line.strip()
            parts = line.split("=")
            key = parts[0]
            val = "=".join(parts[1:])
            if key.startswith("~#"):
                try: data[key] = int(val)
                except ValueError: data[key] = 0
            else:
                if key != "~filename": val = util.decode(val)
                if key in data: data[key] += "\n" + val
                else: data[key] = val
        print to(FileFromPattern(fstring, False).match(AudioFile(data)))
        raise SystemExit
    except (OSError, IOError):
        print to(_("No song is currently playing."))
        raise SystemExit(True)

def isrunning():
    return os.path.exists(const.CONTROL)

def control(c):
    if not isrunning():
        raise SystemExit(to(_("Quod Libet is not running.")))
    else:
        try:
            import signal
            # This is a total abuse of Python! Hooray!
            signal.signal(signal.SIGALRM, lambda: "" + 2)
            signal.alarm(1)
            f = file(const.CONTROL, "w")
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
            f.write(c)
            f.close()
        except (OSError, IOError, TypeError):
            print to(_("Unable to write to %s. Removing it.") % const.CONTROL)
            try: os.unlink(const.CONTROL)
            except OSError: pass
            if c != '!': raise SystemExit(True)
        else:
            raise SystemExit

def enable_periodic_save():
    # Check every 5 minutes to see if the library/config on disk are
    # over 15 minutes old; if so, update them. This function can, in theory,
    # break if saving the library takes more than 5 minutes.
    import gobject, time
    from threading import Thread
    def save(save_library, save_config):
        if (time.time() - os.path.mtime(const.LIBRARY)) > 15*60:
            library.save(const.LIBRARY)
        if (time.time() - os.path.mtime(const.CONFIG)) > 15*60:
            config.write(const.CONFIG)
        thread = Thread(target = save, args = (True, True))
        gobject.timeout_add(5*60, thread.start, priority=gobject.PRIORITY_LOW)
    thread = Thread(target = save, args = (False, False))
    gobject.timeout_add(5*60, thread.start, priority=gobject.PRIORITY_LOW)

def cleanup(*args):
    for filename in [const.CURRENT, const.CONTROL]:
        try: os.unlink(filename)
        except OSError: pass

if __name__ == "__main__":
    basedir = os.path.split(os.path.realpath(__file__))[0]
    sys.path.insert(0, os.path.join(basedir, "quodlibet.zip"))
    i18ndir = "/usr/share/locale"

    import locale, gettext
    try: locale.setlocale(locale.LC_ALL, '')
    except: pass
    from util import to

    gettext.bindtextdomain("quodlibet")
    gettext.textdomain("quodlibet")
    gettext.install("quodlibet", unicode = True)

    import const

    # Check command-line parameters before doing "real" work, so they
    # respond quickly.
    opts = sys.argv[1:]
    controls = {"next": ">", "previous": "<", "play": ")",
                "pause": "|", "play-pause": "-", "volume-up": "v+",
                "volume-down": "v-", }
    controls_opt = { "seek": "s", "shuffle": "&",
                     "repeat": "@", "query": "q", "volume": "v" }

    options = OptionParser(
        "Quod Libet", const.VERSION, 
        _("a music library and player"),
        _("[ --refresh-library | --print-playing | control ]"))

    options.add("refresh-library", help=_("Rescan your library and exit"))
    options.add("print-playing", help=_("Print the playing song and exit"))

    for opt, help in [
        ("next", _("Jump to next song")),
        ("previous", _("Jump to previous song")),
        ("play", _("Start playback")),
        ("pause", _("Pause playback")),
        ("play-pause", _("Toggle play/pause mode")),
        ("volume-up", _("Turn up volume")),
        ("volume-down", _("Turn down volume")),
        ("status", _("Print playing status")),
        ]: options.add(opt, help=help)

    for opt, help, arg in [
        ("seek", _("Seek within the playing song"), _("[+|-][HH:]MM:SS")),
        ("shuffle", _("Turn shuffle off, on, or toggle it"), _("0|1|t")),
        ("repeat", _("Turn repeat off, on, or toggle it"), _("0|1|t")),
        ("volume", _("Set the volume"), _("+|-|0..100")),
        ("query", _("Search your library"), _("search-string")),
        ("play-file", _("Play a file"), _("filename"))
        ]: options.add(opt, help=help, arg=arg)

    opts, args = options.parse()

    for command, arg in opts.items():
        if command == "refresh-library": refresh_cache()
        elif command in controls: control(controls[command])
        elif command in controls_opt:
            control(controls_opt[command] + arg)
        elif command == "status": print_status()
        elif command == "play-file":
            filename = os.path.abspath(os.path.expanduser(arg))
            if os.path.isdir(filename): control("d" + filename)
            else: control("p" + filename)
        elif command == "print-playing":
            try: print_playing(args[0])
            except IndexError: print_playing()

    if os.path.exists(const.CONTROL):
        print _("Quod Libet is already running.")
        control('!')

    # Get to the right directory for our data.
    os.chdir(basedir)
    # Initialize GTK.
    import pygtk
    pygtk.require('2.0')
    import gtk
    if gtk.pygtk_version < (2, 4, 1) or gtk.gtk_version < (2, 6):
        sys.stderr.write(to(_("E: You need GTK+ 2.6 and PyGTK 2.4 or greater to run Quod Libet."))+"\n")
        sys.stderr.write(to(_("E: You have GTK+ %s and PyGTK %s.") % (
            ".".join(map(str, gtk.gtk_version)),
            ".".join(map(str, gtk.pygtk_version)))) + "\n")
        raise SystemExit(to(_("E: Please upgrade GTK+/PyGTK.")))

    import util; from util import to

    # Load configuration data and scan the library for new/changed songs.
    import config
    config.init(const.CONFIG)

    # Load the library.
    import library
    library.init(const.LIBRARY)
    print to(_("Loaded song library."))
    from library import library

    if config.get("settings", "scan"):
        for a, c in library.scan(config.get("settings", "scan").split(":")):
            pass

    # Try to initialize the playlist and audio output.
    print to(_("Opening audio device."))
    import player
    try: player.init(config.get("settings", "backend"))
    except IOError:
        import widgets
        gtk.idle_add(widgets.error_and_quit)
        gtk.main()
        config.write(const.CONFIG)
        raise SystemExit(True)

    try: main()
    finally: cleanup()
