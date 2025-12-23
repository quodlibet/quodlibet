# Copyright 2014,2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
import os

from senf import fsn2text, uri2fsn

from quodlibet import C_, _
from quodlibet.util.dprint import print_, print_e
from quodlibet.remote import Remote, RemoteError


def exit_(status=None, notify_startup=False):
    """Call this to abort the startup before any mainloop starts.

    notify_startup needs to be true if QL could potentially have been
    called from the desktop file.
    """

    if notify_startup:
        import gi

        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk

        Gdk.notify_startup_complete()
    raise SystemExit(status)


def is_running():
    """If maybe is another instance running"""

    return Remote.remote_exists()


def control(command, arg=None, ignore_error=False):
    """Sends command to the existing instance if possible and exits.

    Will print any response it gets to stdout.

    Does not return except if ignore_error is True and sending
    the command failed.
    """

    if not is_running():
        if ignore_error:
            return
        exit_(
            _("Quod Libet is not running (add '--run' to start it)"),
            notify_startup=True,
        )
        return

    message = command
    if arg is not None:
        message += " " + arg

    try:
        response = Remote.send_message(message)
    except RemoteError as e:
        if ignore_error:
            return
        exit_(str(e), notify_startup=True)
    else:
        if response is not None:
            print_(response, end="", flush=True)
        exit_(notify_startup=True)


def process_arguments(argv):
    from quodlibet.util.path import uri_is_valid
    from quodlibet import util
    from quodlibet import const

    actions = []
    controls = [
        "next",
        "previous",
        "play",
        "pause",
        "play-pause",
        "stop",
        "hide-window",
        "show-window",
        "toggle-window",
        "focus",
        "quit",
        "unfilter",
        "refresh",
        "force-previous",
    ]
    controls_opt = [
        "seek",
        "repeat",
        "query",
        "volume",
        "filter",
        "rating",
        "set-browser",
        "open-browser",
        "shuffle",
        "queue",
        "stop-after",
        "random",
        "repeat-type",
        "shuffle-type",
        "add-location",
    ]

    options = util.OptionParser(
        "Quod Libet", const.VERSION, _("a music library and player"), _("[option]")
    )

    options.add("print-playing", help=_("Print the playing song and exit"))
    options.add("start-playing", help=_("Begin playing immediately"))
    options.add("start-hidden", help=_("Don't show any windows on start"))

    for opt, help in [
        ("next", _("Jump to next song")),
        ("previous", _("Jump to previous song or restart if near the beginning")),
        ("force-previous", _("Jump to previous song")),
        ("play", _("Start playback")),
        ("pause", _("Pause playback")),
        ("play-pause", _("Toggle play/pause mode")),
        ("stop", _("Stop playback")),
        ("volume-up", _("Turn up volume")),
        ("volume-down", _("Turn down volume")),
        ("rating-up", _("Increase rating of playing song by one star")),
        ("rating-down", _("Decrease rating of playing song by one star")),
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
        ("print-query-text", _("Print the active text query")),
        ("no-plugins", _("Start without plugins")),
        ("run", _("Start Quod Libet if it isn't running")),
        ("quit", _("Exit Quod Libet")),
    ]:
        options.add(opt, help=help)

    for opt, help, arg in [
        ("seek", _("Seek within the playing song"), _("[+|-][HH:]MM:SS")),
        ("shuffle", _("Set or toggle shuffle mode"), "0|1|t"),
        ("shuffle-type", _("Set shuffle mode type"), "random|weighted|off"),
        ("repeat", _("Turn repeat off, on, or toggle it"), "0|1|t"),
        ("repeat-type", _("Set repeat mode type"), "current|all|one|off"),
        ("volume", _("Set the volume"), "[+|-]0..100"),
        ("query", _("Search your audio library"), _("query")),
        ("play-file", _("Play a file"), C_("command", "filename")),
        ("rating", _("Set rating of playing song"), "[+|-]0.0..1.0"),
        ("set-browser", _("Set the current browser"), "BrowserName"),
        ("stop-after", _("Stop after the playing song"), "0|1|t"),
        ("open-browser", _("Open a new browser"), "BrowserName"),
        ("queue", _("Show or hide the queue"), "on|off|t"),
        ("random", _("Filter on a random value"), C_("command", "tag")),
        ("filter", _("Filter on a tag value"), _("tag=value")),
        (
            "enqueue",
            _("Enqueue a file or query"),
            "{}|{}".format(C_("command", "filename"), _("query")),
        ),
        (
            "enqueue-files",
            _("Enqueue comma-separated files"),
            "{}[,{}..]".format(_("filename"), _("filename")),
        ),
        ("print-query", _("Print filenames of results of query to stdout"), _("query")),
        (
            "unqueue",
            _("Unqueue a file or query"),
            "{}|{}".format(C_("command", "filename"), _("query")),
        ),
        ("add-location", _("Add a file or directory to the library"), _("location")),
        ("with-pattern", _("Set template for --print-* commands"), _("pattern")),
    ]:
        options.add(opt, help=help, arg=arg)

    options.add("sm-config-prefix", arg="dummy")
    options.add("sm-client-id", arg="prefix")
    options.add("screen", arg="dummy")

    def is_vol(str):
        if len(str) == 1 and str[0] in "+-":
            return True
        return is_float(str)

    def is_rate(str):
        if len(str) == 1 and str[0] in "+-":
            return True
        return is_float(str)

    def is_time(str):
        if str[0] not in "+-0123456789":
            return False
        if str[0] in "+-":
            str = str[1:]
        parts = str.split(":")
        if len(parts) > 3:
            return False
        return False not in [p.isdigit() for p in parts]

    def is_float(str):
        try:
            float(str)
        except ValueError:
            return False
        else:
            return True

    validators = {
        "shuffle": ["0", "1", "t", "on", "off", "toggle"].__contains__,
        "shuffle-type": ["random", "weighted", "off", "0"].__contains__,
        "repeat": ["0", "1", "t", "on", "off", "toggle"].__contains__,
        "repeat-type": ["current", "all", "one", "off", "0"].__contains__,
        "volume": is_vol,
        "seek": is_time,
        "rating": is_rate,
        "stop-after": ["0", "1", "t"].__contains__,
    }

    cmds_todo = []

    def queue(*args):
        cmds_todo.append(args)

    # XXX: to make startup work in case the desktop file isn't passed
    # a file path/uri
    if argv[-1] == "--play-file":
        argv = argv[:-1]

    opts, args = options.parse(argv[1:])

    for command, arg in opts.items():
        if command in controls:
            queue(command)
        elif command in controls_opt:
            if command in validators and not validators[command](arg):
                print_e(_("Invalid argument for '%s'.") % command)
                print_e(_("Try %s --help.") % fsn2text(argv[0]))
                exit_(True, notify_startup=True)
            else:
                queue(command, arg)
        elif command == "status":
            queue("status")
        elif command == "print-playlist":
            queue("dump-playlist", opts.get("with-pattern"))
        elif command == "print-queue":
            queue("dump-queue", opts.get("with-pattern"))
        elif command == "list-browsers":
            queue("dump-browsers")
        elif command == "volume-up":
            queue("volume +")
        elif command == "volume-down":
            queue("volume -")
        elif command == "rating-up":
            queue("rating +")
        elif command == "rating-down":
            queue("rating -")
        elif command == "enqueue" or command == "unqueue":
            try:
                filename = uri2fsn(arg)
            except ValueError:
                filename = arg
            queue(command, filename)
        elif command == "enqueue-files":
            queue(command, arg)
        elif command == "play-file":
            if uri_is_valid(arg) and arg.startswith("quodlibet://"):
                # TODO: allow handling of URIs without --play-file
                queue("uri-received", arg)
            else:
                try:
                    filename = uri2fsn(arg)
                except ValueError:
                    filename = arg
                filename = os.path.abspath(os.path.expanduser(arg))
                queue("play-file", filename)
        elif command == "add-location":
            try:
                path = uri2fsn(arg)
            except ValueError:
                path = arg
            path = os.path.abspath(os.path.expanduser(arg))
            queue("add-location", path)
        elif command == "print-playing":
            try:
                queue("print-playing", args[0])
            except IndexError:
                queue("print-playing", opts.get("with-pattern"))
        elif command == "print-query":
            pattern = opts.get("with-pattern")
            queue(command, json.dumps({"query": arg, "pattern": pattern}))
        elif command == "print-query-text":
            queue(command)
        elif command == "start-playing":
            actions.append(command)
        elif command == "start-hidden":
            actions.append(command)
        elif command == "no-plugins":
            actions.append(command)
        elif command == "run":
            actions.append(command)

    if cmds_todo:
        for cmd in cmds_todo:
            control(*cmd, ignore_error="run" in actions)
    else:
        # this will exit if it succeeds
        control("focus", ignore_error=True)

    return actions, cmds_todo
