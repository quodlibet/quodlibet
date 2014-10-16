# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import tempfile
import sys
from quodlibet.util.dprint import print_, print_d, print_e


def print_fifo(command):
    import quodlibet

    if os.name == "nt":
        quodlibet.exit("Sorry, not yet implemented under Windows")

    from quodlibet import const
    from quodlibet.remote import Remote

    if not os.path.exists(const.CURRENT):
        quodlibet.exit("not-running")
    else:
        fd, filename = tempfile.mkstemp()
        try:
            os.unlink(filename)
            # mkfifo fails if the file exists, so this is safe.
            os.mkfifo(filename, 0o600)

            if not Remote.send_message(command + " " + filename):
                raise TypeError

            f = file(filename, "r")
            sys.stdout.write(f.read())
            try:
                os.unlink(filename)
            except EnvironmentError:
                pass
            f.close()
            quodlibet.exit()
        except TypeError:
            try:
                os.unlink(filename)
            except EnvironmentError:
                pass
            quodlibet.exit("not-running")


def print_playing(fstring="<artist~album~tracknumber~title>"):
    import quodlibet
    from quodlibet.formats._audio import AudioFile
    from quodlibet.parse import Pattern
    from quodlibet import const

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
    """Queries library, dumping filenames of matches to stdout
       See Issue 716
    """

    import quodlibet
    import quodlibet.library
    from quodlibet import const, config

    print_d("Querying library for %r" % query)
    if "rating" in query:
        config.init(const.CONFIG)

    library = quodlibet.library.init(const.LIBRARY)
    songs = library.query(query)
    sys.stdout.write("\n".join([song("~filename") for song in songs]) + "\n")
    quodlibet.exit()


def is_running():
    """If there is another instance running"""

    from quodlibet.remote import Remote

    return Remote.remote_exists()


def control(command):
    """Sends command to the existing instance if possible and exits.

    Does not return.
    """

    import quodlibet
    from quodlibet.remote import Remote

    if not is_running():
        quodlibet.exit(_("Quod Libet is not running."), notify_startup=True)
    else:
        ok = Remote.send_message(command)
        quodlibet.exit(0 if ok else 1, notify_startup=True)


def process_arguments():
    import quodlibet
    from quodlibet.util.uri import URI
    from quodlibet import util
    from quodlibet import const

    actions = []
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
        ("list-browsers", _("List available browsers")),
        ("print-playlist", _("Print the current playlist")),
        ("print-queue", _("Print the contents of the queue")),
        ("no-plugins", _("Start without plugins")),
        ("quit", _("Exit Quod Libet")),
            ]:
        options.add(opt, help=help)

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
            ]:
        options.add(opt, help=help, arg=arg)

    options.add("sm-config-prefix", arg="dummy")
    options.add("sm-client-id", arg="prefix")
    options.add("screen", arg="dummy")

    def is_vol(str):
        if str[0] in '+-':
            if len(str) == 1:
                return True
            str = str[1:]
        return str.isdigit()

    def is_time(str):
        if str[0] not in "+-0123456789":
            return False
        elif str[0] in "+-":
            str = str[1:]
        parts = str.split(":")
        if len(parts) > 3:
            return False
        else:
            return not (False in [p.isdigit() for p in parts])

    def is_float(str):
        try:
            float(str)
        except ValueError:
            return False
        else:
            return True

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
        if command in controls:
            control(command)
        elif command in controls_opt:
            if command in validators and not validators[command](arg):
                print_e(_("Invalid argument for '%s'.") % command)
                print_e(_("Try %s --help.") % sys.argv[0])
                quodlibet.exit(True, notify_startup=True)
            else:
                control(command + " " + arg)
        elif command == "status":
            print_fifo("status")
        elif command == "print-playlist":
            print_fifo("dump-playlist")
        elif command == "print-queue":
            print_fifo("dump-queue")
        elif command == "list-browsers":
            print_fifo("dump-browsers")
        elif command == "volume-up":
            control("volume +")
        elif command == "volume-down":
            control("volume -")
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
                filename = os.path.abspath(util.path.expanduser(arg))
            if os.path.isdir(filename):
                control("add-directory " + filename)
            else:
                control("add-file " + filename)
        elif command == "print-playing":
            try:
                print_playing(args[0])
            except IndexError:
                print_playing()
        elif command == "print-query":
            print_query(arg)
        elif command == "start-playing":
            actions.append(command)
        elif command == "no-plugins":
            actions.append(command)

    return actions
