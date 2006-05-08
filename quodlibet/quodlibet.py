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

import os
import signal
import sys

global play
play = False

def main():
    # Load configuration data and scan the library for new/changed songs.
    config.init(const.CONFIG)
    library = load_library()
    player = load_player()

    import util
    import widgets

    util.mkdir(const.USERDIR)
    SIGNALS = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]

    try: ratings = config.getint("settings", "ratings")
    except (ValueError, TypeError): pass
    else: util.RATING_PRECISION = 1.0/ratings

    locale.getlocale(locale.LC_NUMERIC)
    window = widgets.init(player, library)
    if "--debug" not in sys.argv:
        enable_periodic_save(library)
        gtk.quit_add(1, widgets.save_library, window, player, library)
    for sig in SIGNALS: signal.signal(sig, gtk.main_quit)
    gtk.threads_init()
    if play: player.playlist.paused = False
    gtk.main()

def print_fifo(command):
    if not os.path.exists(const.CURRENT):
        raise SystemExit("not-running")
    else:
        from tempfile import mkstemp
        fd, filename = mkstemp()
        try:
            os.unlink(filename)
            # mkfifo fails if the file exists, so this is safe.
            os.mkfifo(filename, 0600)

            signal.signal(signal.SIGALRM, lambda: "" + 2)
            signal.alarm(1)
            f = file(const.CONTROL, "w")
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
            f.write(command + " " + filename)
            f.close()

            f = file(filename, "r")
            sys.stdout.write(f.read())
            try: os.unlink(filename)
            except EnvironmentError: pass
            f.close()
            raise SystemExit
        except TypeError:
            try: os.unlink(filename)
            except EnvironmentError: pass
            raise SystemExit("not-running")

def refresh_cache():
    import config
    import const
    import library

    if isrunning():
        raise SystemExit(to(_(
            "The library cannot be refreshed while Quod Libet is running.")))

    config.init(const.CONFIG)
    lib = library.init()
    print to(_("Loading, scanning, and saving your library."))
    lib.load(const.LIBRARY)
    for x, y in lib.rebuild(): pass
    lib.save(const.LIBRARY)
    raise SystemExit

def print_playing(fstring = "<artist~album~tracknumber~title>"):
    import util

    from formats._audio import AudioFile
    from parse import Pattern

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
        print to(Pattern(fstring).format(AudioFile(data)))
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
            if c != 'focus': raise SystemExit(True)
        else:
            raise SystemExit

def enable_periodic_save(library):
    # Check every 5 minutes to see if the library/config on disk are
    # over 15 minutes old; if so, update them. This function can, in theory,
    # break if saving the library takes more than 5 minutes.
    import time
    import gobject
    import util

    from threading import Thread

    def save():
        if (time.time() - util.mtime(const.LIBRARY)) > 15*60:
            library.save(const.LIBRARY)
        if (time.time() - util.mtime(const.CONFIG)) > 15*60:
            config.write(const.CONFIG)
        thread = Thread(target=save)
        gobject.timeout_add(
            5*60000, thread.start, priority=gobject.PRIORITY_LOW)
    thread = Thread(target=save)
    gobject.timeout_add(5*60000, thread.start, priority=gobject.PRIORITY_LOW)

def process_arguments():
    controls = ["next", "previous", "play", "pause", "play-pause",
                "hide-window", "show-window", "toggle-window",
                "focus", "quit"]
    controls_opt = ["seek", "order", "repeat", "query", "volume", "filter",
                    "set-rating", "set-browser", "open-browser", "random",
                    "song-list", "queue", "enqueue"]

    from util import OptionParser
    options = OptionParser(
        "Quod Libet", const.VERSION, 
        _("a music library and player"),
        _("[ --refresh-library | --print-playing | control ]"))

    options.add("refresh-library", help=_("Rescan your library and exit"))
    options.add("print-playing", help=_("Print the playing song and exit"))
    options.add("start-playing", help=_("Begin playing immediately"))

    for opt, help in [
        ("next", _("Jump to next song")),
        ("previous", _("Jump to previous song")),
        ("play", _("Start playback")),
        ("pause", _("Pause playback")),
        ("play-pause", _("Toggle play/pause mode")),
        ("volume-up", _("Turn up volume")),
        ("volume-down", _("Turn down volume")),
        ("status", _("Print player status")),
        ("hide-window", _("Hide main window")),
        ("show-window", _("Show main window")),
        ("toggle-window", _("Toggle main window visibility")),
        ("focus", _("Focus the running player")),
        ("print-playlist", _("Print the current playlist")),
        ("print-queue", _("Print the contents of the queue")),
        ("quit", _("Exit Quod Libet")),
        ]: options.add(opt, help=help)

    for opt, help, arg in [
        ("seek", _("Seek within the playing song"), _("[+|-][HH:]MM:SS")),
        ("order", _("Set or toggle the playback order"),
         "[order]|toggle"),
        ("repeat", _("Turn repeat off, on, or toggle it"), "0|1|t"),
        ("volume", _("Set the volume"), "+|-|0..100"),
        ("query", _("Search your audio library"), _("query")),
        ("play-file", _("Play a file"), _("filename")),
        ("set-rating", _("Rate the playing song"), "0.0..1.0"),
        ("set-browser", _("Set the current browser"), "BrowserName"),
        ("open-browser", _("Open a new browser"), "BrowserName"),
        ("queue", _("Show or hide the queue"), "on|off|t"),
        ("song-list", _("Show or hide the main song list"), "on|off|t"),
        ("random", _("Filter on a random value"), _("tag")),
        ("filter", _("Filter on a tag value"), _("tag=value")),
        ("enqueue", _("Enqueue a file or query"), "%s|%s" %(
        _("filename"),_( "query"))),
        ]: options.add(opt, help=help, arg=arg)

    options.add("sm-config-prefix", arg="dummy")
    options.add("sm-client-id", arg="prefix")
    options.add("screen", arg="dummy")

    def is_time(str):
        if str[0] not in "+-0123456789": return False
        elif str[0] in "+-": str = str[1:]
        parts = str.split(":")
        if len(parts) > 3: return False
        else: return not (False in [p.isdigit() for p in parts])
    def is_float(str):
        try: float(str)
        except ValueError: return False
        else: return True

    validators = {
        "order": ["0", "1", "t", "toggle", "inorder", "shuffle",
                  "weighted", "onesong"].__contains__,
        "repeat": ["0", "1", "t", "on", "off", "toggle"].__contains__,
        "volume": str.isdigit,
        "seek": is_time,
        "set-rating": is_float,
        }

    opts, args = options.parse()

    for command, arg in opts.items():
        if command == "refresh-library": refresh_cache()
        elif command in controls: control(command)
        elif command in controls_opt:
            if command in validators and not validators[command](arg):
                sys.stderr.write(
                    to(_("E: Invalid argument for '%s'.") % command))
                sys.stderr.write("\n")
                raise SystemExit(to(_("E: Try %s --help.") % sys.argv[0]))
            else: control(command + " " + arg)
        elif command == "status": print_fifo("status")
        elif command == "print-playlist": print_fifo("dump-playlist")
        elif command == "print-queue": print_fifo("dump-queue")
        elif command == "volume-up": control("volume +")
        elif command == "volume-down": control("volume -")
        elif command == "play-file":
            filename = os.path.abspath(os.path.expanduser(arg))
            if os.path.isdir(filename): control("add-directory " + filename)
            else: control("add-file " + filename)
        elif command == "print-playing":
            try: print_playing(args[0])
            except IndexError: print_playing()
        elif command == "start-playing":
            global play
            play = True

def load_library():
    import library
    library.init(const.LIBRARY)
    print to(_("Loaded song library."))
    from library import library

    if config.get("settings", "scan"):
        for a, c, r in library.scan(config.get("settings", "scan").split(":")):
            pass
    return library

def load_player():
    # Try to initialize the playlist and audio output.
    print to(_("Opening audio device."))
    import player
    sink = config.get("settings", "pipeline")
    try: playlist = player.init(sink)
    except player.NoSinkError:
        import widgets, gobject
        gobject.idle_add(widgets.no_sink_quit, sink)
        gtk.main()
        config.write(const.CONFIG)
        raise SystemExit(True)
    except player.NoSourceError:
        import widgets, gobject
        gobject.idle_add(widgets.no_source_quit)
        gtk.main()
        config.write(const.CONFIG)
        raise SystemExit(True)
    else: return playlist

if __name__ == "__main__":
    basedir = os.path.dirname(os.path.realpath(__file__))
    if basedir.endswith("/share/quodlibet"):
        sys.path.append(basedir[:-15] + "lib/quodlibet")

    import locale, util
    util.gettext_install("quodlibet", unicode=True)
    util.ctypes_init()

    from util import to
    import const
    if "--debug" not in sys.argv:
        process_arguments()
        if os.path.exists(const.CONTROL):
            print to(_("Quod Libet is already running."))
            control('focus')

    # Initialize GTK.
    util.gtk_init()
    import gtk

    import pygst
    pygst.require('0.10')

    import config
    main()
