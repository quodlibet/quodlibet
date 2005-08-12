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

def main():
    import signal, gtk, widgets, player, library
    gtk.threads_init()

    SIGNALS = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]

    window = widgets.init()

    from threading import Thread
    enable_periodic_save()
    gtk.threads_enter()
    song = library.library.get(config.get("memory", "song"))
    t = Thread(
        target=player.playlist.play, args=(widgets.widgets.watcher, song))
    gtk.quit_add(1, widgets.save_library, t)
    for sig in SIGNALS: signal.signal(sig, gtk.main_quit)
    t.start()
    gtk.main()
    gtk.threads_leave()

def print_status():
    if not os.path.exists(const.CURRENT): print "stopped"
    elif os.path.exists(const.PAUSED): print "paused"
    else: print "playing"
    raise SystemExit

def refresh_cache():
    if isrunning():
        raise SystemExit(to(_(
            "The library cannot be refreshed while Quod Libet is running.")))
    import library, config, const
    config.init(const.CONFIG)
    lib = library.init()
    print to(_("Loading, scanning, and saving your library."))
    lib.load(const.LIBRARY)
    for x, y in lib.rebuild(): pass
    lib.save(const.LIBRARY)
    raise SystemExit

def print_playing(fstring = "<artist~album~tracknumber~title>"):
    import util
    from util import to, FileFromPattern
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
    import gobject, time, util
    from library import library
    from threading import Thread
    def save(save_library, save_config):
        if (time.time() - util.mtime(const.LIBRARY)) > 15*60:
            library.save(const.LIBRARY)
        if (time.time() - util.mtime(const.CONFIG)) > 15*60:
            config.write(const.CONFIG)
        thread = Thread(target=save, args=(True, True))
        gobject.timeout_add(5*60, thread.start, priority=gobject.PRIORITY_LOW)
    thread = Thread(target=save, args=(False, False))
    gobject.timeout_add(5*60, thread.start, priority=gobject.PRIORITY_LOW)

def process_arguments():
    controls = {"next": ">", "previous": "<", "play": ")",
                "pause": "|", "play-pause": "-", "volume-up": "v+",
                "volume-down": "v-", }
    controls_opt = { "seek": "s", "shuffle": "&",
                     "repeat": "@", "query": "q", "volume": "v" }

    from util import OptionParser
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
        ("shuffle", _("Turn shuffle off, on, or toggle it"), "0|1|t"),
        ("repeat", _("Turn repeat off, on, or toggle it"), "0|1|t"),
        ("volume", _("Set the volume"), "+|-|0..100"),
        ("query", _("Search your audio library"), _("search-string")),
        ("play-file", _("Play a file"), _("filename"))
        ]: options.add(opt, help=help, arg=arg)

    def is_time(str):
        if str[0] not in "+-0123456789": return False
        elif str[0] in "+-": str = str[1:]
        parts = str.split(":")
        if len(parts) > 3: return False
        else: return not (False in [p.isdigit() for p in parts])

    validators = {"shuffle": lambda a: a in list("012t"),
                  "repeat": lambda a: a in list("01t"),
                  "volume": str.isdigit,
                  "seek": is_time,
                  }

    opts, args = options.parse()

    for command, arg in opts.items():
        if command == "refresh-library": refresh_cache()
        elif command in controls:
            control(controls[command])
        elif command in controls_opt:
            if command in validators and not validators[command](arg):
                sys.stderr.write(
                    to(_("E: Invalid argument for '%s'.") % command))
                sys.stderr.write("\n")
                raise SystemExit(to(_("E: Try %s --help.") % sys.argv[0]))
            else:  control(controls_opt[command] + arg)
        elif command == "status": print_status()
        elif command == "play-file":
            filename = os.path.abspath(os.path.expanduser(arg))
            if os.path.isdir(filename): control("d" + filename)
            else: control("p" + filename)
        elif command == "print-playing":
            try: print_playing(args[0])
            except IndexError: print_playing()

def load_library():
    import library
    library.init(const.LIBRARY)
    print to(_("Loaded song library."))
    from library import library

    if config.get("settings", "scan"):
        for a, c, r in library.scan(config.get("settings", "scan").split(":")):
            pass

def load_player():
    # Try to initialize the playlist and audio output.
    print to(_("Opening audio device."))
    import player
    try: player.init(config.get("settings", "backend"))
    except IOError:
        import widgets, gobject
        gobject.idle_add(widgets.error_and_quit)
        gtk.main()
        config.write(const.CONFIG)
        raise SystemExit(True)

if __name__ == "__main__":
    basedir = os.path.split(os.path.realpath(__file__))[0]
    sys.path.insert(0, os.path.join(basedir, "quodlibet.zip"))
    i18ndir = "/usr/share/locale"

    import locale, gettext
    try: locale.setlocale(locale.LC_ALL, '')
    except: pass

    gettext.bindtextdomain("quodlibet")
    gettext.textdomain("quodlibet")
    gettext.install("quodlibet", unicode=True)

    from util import to
    import const
    process_arguments()
    if os.path.exists(const.CONTROL):
        print _("Quod Libet is already running.")
        control('!')

    # Get to the right directory for our data.
    os.chdir(basedir)
    # Initialize GTK.
    import pygtk
    pygtk.require('2.0')
    import gtk
    if gtk.pygtk_version < (2, 6) or gtk.gtk_version < (2, 6):
        sys.stderr.write(
            to(_("E: You need GTK+ 2.6 and PyGTK 2.6 or greater."))+"\n")
        sys.stderr.write(to(_("E: You have GTK+ %s and PyGTK %s.") % (
            ".".join(map(str, gtk.gtk_version)),
            ".".join(map(str, gtk.pygtk_version)))) + "\n")
        raise SystemExit(to(_("E: Please upgrade GTK+/PyGTK.")))

    import util; from util import to

    # Load configuration data and scan the library for new/changed songs.
    import config
    config.init(const.CONFIG)
    load_library()
    load_player()
    main()
