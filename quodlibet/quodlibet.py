#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
# <quod-libet-development@googlegroups.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

import os
import signal
import sys
import tempfile
import time

import quodlibet, quodlibet.player

from quodlibet import config
from quodlibet import const
from quodlibet import util

from threading import Thread

global play
play = False

def main():
    config.init(const.CONFIG)

    try:
        backend, library, player = quodlibet.init(
            backend=config.get("player", "backend"),
            library=const.LIBRARY,
            )
    except quodlibet.player.error, error:
        import gobject
        import gtk
        gobject.idle_add(quodlibet.error_and_quit, error)
        gobject.idle_add(gtk.main_quit)
        gtk.main()
        config.write(const.CONFIG)
        raise SystemExit(True)

    from quodlibet import widgets

    try: ratings = config.getint("settings", "ratings")
    except (ValueError, TypeError): pass
    else: util.RATING_PRECISION = 1.0/ratings

    try: default_rating = config.getfloat("settings", "default_rating")
    except (ValueError, TypeError): pass
    else: const.DEFAULT_RATING = default_rating

    window = widgets.init(player, library)
    if "--debug" not in sys.argv:
        enable_periodic_save(library)
    if play:
        player.paused = False
    quodlibet.main(window)
    quodlibet.quit((backend, library, player), save=True)
    try: config.write(const.CONFIG)
    except EnvironmentError, err: pass

def print_fifo(command):
    if not os.path.exists(const.CURRENT):
        raise SystemExit("not-running")
    else:
        fd, filename = tempfile.mkstemp()
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

def print_playing(fstring="<artist~album~tracknumber~title>"):
    from quodlibet.formats._audio import AudioFile
    from quodlibet.parse import Pattern

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
        print_(Pattern(fstring).format(AudioFile(data)))
        raise SystemExit
    except (OSError, IOError):
        print_(_("No song is currently playing."))
        raise SystemExit(True)

def isrunning():
    return os.path.exists(const.CONTROL)

def control(c):
    if not isrunning():
        raise SystemExit(_("Quod Libet is not running."))
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
            print_w(_("Unable to write to %s. Removing it.") % const.CONTROL)
            try: os.unlink(const.CONTROL)
            except OSError: pass
            if c != 'focus':
                raise SystemExit(True)
        else:
            raise SystemExit

def enable_periodic_save(library):
    # Check every 5 minutes to see if the library/config on disk are
    # over 15 minutes old; if so, update them. This function can, in theory,
    # break if saving the library takes more than 5 minutes.
    import gobject

    def save():
        if library.dirty:
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
                "focus", "quit", "unfilter", "refresh"]
    controls_opt = ["seek", "order", "repeat", "query", "volume", "filter",
                    "set-rating", "set-browser", "open-browser", "random",
                    "song-list", "queue", "enqueue", "unqueue"]

    options = util.OptionParser(
        "Quod Libet", const.VERSION, 
        _("a music library and player"),
        _("[ --print-playing | control ]"))

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
        ("unfilter", _("Remove active browser filters")),
        ("refresh", _("Refresh and rescan library")),
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
        ("play-file", _("Play a file"), Q_("command|filename")),
        ("set-rating", _("Rate the playing song"), "0.0..1.0"),
        ("set-browser", _("Set the current browser"), "BrowserName"),
        ("open-browser", _("Open a new browser"), "BrowserName"),
        ("queue", _("Show or hide the queue"), "on|off|t"),
        ("song-list", _("Show or hide the main song list"), "on|off|t"),
        ("random", _("Filter on a random value"), Q_("command|tag")),
        ("filter", _("Filter on a tag value"), _("tag=value")),
        ("enqueue", _("Enqueue a file or query"), "%s|%s" %(
        Q_("command|filename"), _("query"))),
        ("unqueue", _("Unqueue a file or query"), "%s|%s" %(
        Q_("command|filename"), _("query"))),
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
        if command in controls: control(command)
        elif command in controls_opt:
            if command in validators and not validators[command](arg):
                print_e(_("Invalid argument for '%s'.") % command)
                print_e(_("Try %s --help.") % sys.argv[0])
                raise SystemExit(True)
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

if __name__ == "__main__":
    process_arguments()
    if isrunning() and not os.environ.get("QUODLIBET_DEBUG"):
        print_(_("Quod Libet is already running."))
        control('focus')
    main()
