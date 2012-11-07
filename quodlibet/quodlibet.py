#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
# <quod-libet-development@googlegroups.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

0<>0 # Python 3.x not supported! Use 2.6+ instead.

import os
import signal
import sys
import tempfile

import quodlibet
import quodlibet.player

from quodlibet import app
from quodlibet import config
from quodlibet import browsers
from quodlibet import const
from quodlibet import util
from quodlibet.util.uri import URI

play = False
no_plugins = False


def main():
    quodlibet._init_signal()

    process_arguments()
    if isrunning() and not quodlibet.const.DEBUG:
        print_(_("Quod Libet is already running."))
        control('focus')

    config.init(const.CONFIG)

    library = quodlibet.init(library=const.LIBRARY,
                             icon="quodlibet",
                             name="Quod Libet",
                             title=const.PROCESS_TITLE_QL)
    app.library = library
    app.librarian = library.librarian

    for backend in [config.get("player", "backend"), "nullbe"]:
        try:
            player = quodlibet.init_backend(backend, app.librarian)
        except quodlibet.player.error, error:
            print_e("%s. %s" % (error.short_desc, error.long_desc))
        else:
            break
    app.player = player

    os.environ["PULSE_PROP_media.role"] = "music"
    os.environ["PULSE_PROP_application.icon_name"] = "quodlibet"

    browsers.init()

    from quodlibet.qltk.songlist import SongList

    try: ratings = config.getint("settings", "ratings")
    except (ValueError, TypeError): pass
    else: util.RATING_PRECISION = 1.0/ratings

    try: default_rating = config.getfloat("settings", "default_rating")
    except (ValueError, TypeError): pass
    else: const.DEFAULT_RATING = default_rating

    try: symbol = config.get("settings", "rating_symbol").decode("utf-8")
    except UnicodeDecodeError: pass
    else: util.RATING_SYMBOL = symbol

    if config.get("settings", "headers").split() == []:
       config.set("settings", "headers", "title")
    headers = config.get("settings", "headers").split()
    SongList.set_all_column_headers(headers)

    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        util.tags.add(opt, val)

    in_all =("~filename ~uri ~#lastplayed ~#rating ~#playcount ~#skipcount "
             "~#added ~#bitrate ~current ~#laststarted ~basename "
             "~dirname").split()
    for Kind in browsers.browsers:
        if Kind.headers is not None: Kind.headers.extend(in_all)
        Kind.init(library)

    pm = quodlibet.init_plugins(no_plugins)

    if hasattr(player, "init_plugins"):
        player.init_plugins()

    from quodlibet.qltk.songsmenu import SongsMenu
    SongsMenu.init_plugins()

    from quodlibet.qltk.quodlibetwindow import QuodLibetWindow
    app.window = window = QuodLibetWindow(library, player)

    from quodlibet.plugins.events import EventPluginHandler
    pm.register_handler(EventPluginHandler(library.librarian, player))

    from quodlibet.qltk import mmkeys_ as mmkeys
    from quodlibet.qltk.remote import FSInterface, FIFOControl
    from quodlibet.qltk.tracker import SongTracker
    try:
        from quodlibet.qltk.dbus_ import DBusHandler
    except ImportError:
        DBusHandler = lambda player, library: None

    mmkeys.init(window, player)
    FSInterface(player)
    FIFOControl(library, window, player)
    DBusHandler(player, library)
    SongTracker(library.librarian, player, window.playlist)

    from quodlibet.qltk import session
    session.init("quodlibet")

    quodlibet.enable_periodic_save(save_library=True)

    if play:
        player.paused = False

    quodlibet.main(window)

    print_d("Shutting down player device %r." % player.version_info)
    quodlibet.player.quit(player)
    quodlibet.library.save(force=True)

    config.save(const.CONFIG)

    print_d("Finished shutdown.")


def print_fifo(command):
    if not os.path.exists(const.CURRENT):
        quodlibet.exit("not-running")
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
            quodlibet.exit()
        except TypeError:
            try: os.unlink(filename)
            except EnvironmentError: pass
            quodlibet.exit("not-running")

def print_playing(fstring="<artist~album~tracknumber~title>"):
    from quodlibet.formats._audio import AudioFile
    from quodlibet.parse import Pattern

    try:
        text = open(const.CURRENT, "rb").read()
        song = AudioFile()
        song.from_dump(text)
        print_(Pattern(fstring).format(song))
        quodlibet.exit()
    except (OSError, IOError):
        print_(_("No song is currently playing."))
        quodlibet.exit(True)

def print_query(query):
    '''Queries library, dumping filenames of matches to stdout

        See Issue 716
    '''
    print_d("Querying library for %r" %query)
    import quodlibet.library
    library = quodlibet.library.init(const.LIBRARY)
    songs = library.query(query)
    #songs.sort()
    sys.stdout.write("\n".join([song("~filename") for song in songs]) + "\n")
    quodlibet.exit()

def isrunning():
    return os.path.exists(const.CONTROL)

def control(c):
    if not isrunning():
        quodlibet.exit(_("Quod Libet is not running."))
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
                raise quodlibet.exit(True)
        else:
            quodlibet.exit()

def process_arguments():
    controls = ["next", "previous", "play", "pause", "play-pause", "stop",
                "hide-window", "show-window", "toggle-window",
                "focus", "quit", "unfilter", "refresh", "force-previous"]
    controls_opt = ["seek", "order", "repeat", "query", "volume", "filter",
                    "set-rating", "set-browser", "open-browser", "random",
                    "song-list", "queue"]

    options = util.OptionParser(
        "Quod Libet", const.VERSION,
        _("a music library and player"),
        _("[option]"))

    options.add("print-playing", help=_("Print the playing song and exit"))
    options.add("start-playing", help=_("Begin playing immediately"))

    for opt, help in [
        ("next", _("Jump to next song")),
        ("previous",
            _("Jump to previous song or restart if near the beginning")),
        ("force-previous", _("Jump to previous song")),
        ("play", _("Start playback")),
        ("pause", _("Pause playback")),
        ("play-pause", _("Toggle play/pause mode")),
        ("stop", _("Stop playback")),
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
        ("no-plugins", _("Start without plugins")),
        ("quit", _("Exit Quod Libet")),
        ]: options.add(opt, help=help)

    for opt, help, arg in [
        ("seek", _("Seek within the playing song"), _("[+|-][HH:]MM:SS")),
        ("order", _("Set or toggle the playback order"),
            "[order]|toggle"),
        ("repeat", _("Turn repeat off, on, or toggle it"), "0|1|t"),
        ("volume", _("Set the volume"), "(+|-|)0..100"),
        ("query", _("Search your audio library"), _("query")),
        ("play-file", _("Play a file"), Q_("command|filename")),
        ("set-rating", _("Rate the playing song"), "0.0..1.0"),
        ("set-browser", _("Set the current browser"), "BrowserName"),
        ("open-browser", _("Open a new browser"), "BrowserName"),
        ("queue", _("Show or hide the queue"), "on|off|t"),
        ("song-list", _("Show or hide the main song list"), "on|off|t"),
        ("random", _("Filter on a random value"), Q_("command|tag")),
        ("filter", _("Filter on a tag value"), _("tag=value")),
        ("enqueue", _("Enqueue a file or query"), "%s|%s" % (
            Q_("command|filename"), _("query"))),
        ("enqueue-files", _("Enqueue comma-separated files"), "%s[,%s..]" % (
            _("filename"), _("filename"))),
        ("print-query", _("Print filenames of results of query to stdout"), 
            _("query")),
        ("unqueue", _("Unqueue a file or query"), "%s|%s" % (
            Q_("command|filename"), _("query"))),
        ]: options.add(opt, help=help, arg=arg)

    options.add("sm-config-prefix", arg="dummy")
    options.add("sm-client-id", arg="prefix")
    options.add("screen", arg="dummy")

    def is_vol(str):
        if str[0] in '+-':
            if len(str) == 1: return True
            str = str[1:]
        return str.isdigit()
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
        "volume": is_vol,
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
                quodlibet.exit(True)
            else: control(command + " " + arg)
        elif command == "status": print_fifo("status")
        elif command == "print-playlist": print_fifo("dump-playlist")
        elif command == "print-queue": print_fifo("dump-queue")
        elif command == "volume-up": control("volume +")
        elif command == "volume-down": control("volume -")
        elif command == "enqueue" or command == "unqueue":
            try:
                filename = URI(arg).filename
            except ValueError:
                filename = arg
            control(command + " " + filename)
        elif command == "enqueue-files":
            control(command + " " + arg)
        elif command == "play-file":
            try:
                filename = URI(arg).filename
            except ValueError:
                filename = os.path.abspath(util.expanduser(arg))
            if os.path.isdir(filename): control("add-directory " + filename)
            else: control("add-file " + filename)
        elif command == "print-playing":
            try: print_playing(args[0])
            except IndexError: print_playing()
        elif command == "print-query":
            print_query(arg)
        elif command == "start-playing":
            global play
            play = True
        elif command == "no-plugins":
            global no_plugins
            no_plugins = True

if __name__ == "__main__":
    main()
