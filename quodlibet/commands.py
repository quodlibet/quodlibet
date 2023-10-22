# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna,
#           2011-2020 Nick Boultbee
#           2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
import os

from senf import uri2fsn, fsnative, fsn2text, text2fsn

from quodlibet.util.string import split_escape

from quodlibet import browsers

from quodlibet import util
from quodlibet.util import print_d, print_e, copool

from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.properties import SongProperties
from quodlibet.util.library import scan_library

from quodlibet.order.repeat import RepeatListForever, RepeatSongForever, OneSong
from quodlibet.order.reorder import OrderWeighted, OrderShuffle
from quodlibet.pattern import Pattern

from quodlibet.config import RATINGS


class CommandError(Exception):
    pass


class CommandRegistry:
    """Knows about all commands and handles parsing/executing them"""

    def __init__(self):
        self._commands = {}

    def register(self, name, args=0, optional=0):
        """Register a new command function

        The functions gets zero or more arguments as `fsnative`
        and should return `None` or `fsnative`. In case an error
        occurred the command should raise `CommandError`.

        Args:
            name (str): the command name
            args (int): amount of required arguments
            optional (int): amount of additional optional arguments
        Returns:
            Callable
        """

        def wrap(func):
            self._commands[name] = (func, args, optional)
            return func

        return wrap

    def handle_line(self, app, line):
        """Parses a command line and executes the command.

        Can not fail.

        Args:
            app (Application)
            line (fsnative)
        Returns:
            fsnative or None
        """

        assert isinstance(line, fsnative)

        # only one arg supported atm
        parts = line.split(" ", 1)
        command = parts[0]
        args = parts[1:]

        print_d("command: %r(*%r)" % (command, args))

        try:
            return self.run(app, command, *args)
        except CommandError as e:
            print_e(e)
            util.print_exc()
        except Exception:
            util.print_exc()

    def run(self, app, name, *args):
        """Execute the command `name` passing args

        May raise CommandError
        """

        if name not in self._commands:
            raise CommandError("Unknown command %r" % name)

        cmd, argcount, optcount = self._commands[name]
        if len(args) < argcount:
            raise CommandError("Not enough arguments for %r" % name)
        if len(args) > argcount + optcount:
            raise CommandError("Too many arguments for %r" % name)

        print_d("Running %r with params %s " % (cmd.__name__, args))

        try:
            result = cmd(app, *args)
        except CommandError as e:
            raise CommandError("%s: %s" % (name, str(e))) from e
        else:
            if result is not None and not isinstance(result, fsnative):
                raise CommandError(
                    "%s: returned %r which is not fsnative" % (name, result))
            return result


def arg2text(arg):
    """Like fsn2text but is strict by default and raises CommandError"""

    try:
        return fsn2text(arg, strict=True)
    except ValueError as e:
        raise CommandError(e) from e


def make_pattern(fstring, default):
    if fstring is None:
        return Pattern(default)
    return Pattern(arg2text(fstring))


registry = CommandRegistry()


@registry.register("previous")
def _previous(app):
    app.player.previous()


@registry.register("force-previous")
def _force_previous(app):
    app.player.previous(True)


@registry.register("next")
def _next(app):
    app.player.next()


@registry.register("pause")
def _pause(app):
    app.player.paused = True


@registry.register("play")
def _play(app):
    app.player.play()


@registry.register("play-pause")
def _play_pause(app):
    app.player.playpause()


@registry.register("stop")
def _stop(app):
    app.player.stop()


@registry.register("focus")
def _focus(app):
    app.present()


@registry.register("volume", args=1)
def _volume(app, value):
    if not value:
        raise CommandError("invalid arg")

    if value[0] in ("+", "-"):
        if len(value) > 1:
            try:
                change = (float(value[1:]) / 100.0)
            except ValueError:
                return
        else:
            change = 0.05
        if value[0] == "-":
            change = -change
        volume = app.player.volume + change
    else:
        try:
            volume = (float(value) / 100.0)
        except ValueError:
            return
    app.player.volume = min(1.0, max(0.0, volume))


@registry.register("stop-after", args=1)
def _stop_after(app, value):
    po = app.player_options
    if value == "0":
        po.stop_after = False
    elif value == "1":
        po.stop_after = True
    elif value == "t":
        po.stop_after = not po.stop_after
    else:
        raise CommandError("Invalid value %r" % value)


@registry.register("shuffle", args=1)
def _shuffle(app, value):
    po = app.player_options
    if value in ["0", "off"]:
        po.shuffle = False
    elif value in ["1", "on"]:
        po.shuffle = True
    elif value in ["t", "toggle"]:
        po.shuffle = not po.shuffle


@registry.register("shuffle-type", args=1)
def _shuffle_type(app, value):
    if value in ["random", "weighted"]:
        app.player_options.shuffle = True
        if value == "random":
            app.window.order.shuffler = OrderShuffle
        elif value == "weighted":
            app.window.order.shuffler = OrderWeighted
    elif value in ["off", "0"]:
        app.player_options.shuffle = False


@registry.register("repeat", args=1)
def _repeat(app, value):
    po = app.player_options
    if value in ["0", "off"]:
        po.repeat = False
    elif value in ["1", "on"]:
        print_d("Enabling repeat")
        po.repeat = True
    elif value in ["t", "toggle"]:
        po.repeat = not po.repeat


@registry.register("repeat-type", args=1)
def _repeat_type(app, value):
    if value in ["current", "all", "one"]:
        app.player_options.repeat = True
        if value == "current":
            app.window.order.repeater = RepeatSongForever
        elif value == "all":
            app.window.order.repeater = RepeatListForever
        elif value == "one":
            app.window.order.repeater = OneSong
    elif value in ["off", "0"]:
        app.player_options.repeat = False


@registry.register("seek", args=1)
def _seek(app, time):
    player = app.player
    if not player.song:
        return
    seek_to = player.get_position()
    if time[0] == "+":
        seek_to += util.parse_time(time[1:]) * 1000
    elif time[0] == "-":
        seek_to -= util.parse_time(time[1:]) * 1000
    else:
        seek_to = util.parse_time(time) * 1000
    seek_to = min(player.song.get("~#length", 0) * 1000 - 1,
                  max(0, seek_to))
    player.seek(seek_to)


@registry.register("play-file", args=1)
def _play_file(app, value):
    app.window.open_file(value)


@registry.register("add-location", args=1)
def _add_location(app, value):
    if os.path.isfile(value):
        ret = app.library.add_filename(value)
        if not ret:
            print_e("Couldn't add file to library")
    elif os.path.isdir(value):
        copool.add(app.library.scan, [value], cofuncid="library",
                   funcid="library")
    else:
        print_e("Invalid location")


@registry.register("toggle-window")
def _toggle_window(app):
    if app.window.get_property("visible"):
        app.hide()
    else:
        app.show()


@registry.register("hide-window")
def _hide_window(app):
    app.hide()


@registry.register("show-window")
def _show_window(app):
    app.show()


@registry.register("rating", args=1)
def _rating(app, value):
    song = app.player.song
    if not song:
        return

    if value[0] in ("+", "-"):
        if len(value) > 1:
            try:
                change = float(value[1:])
            except ValueError:
                return
        else:
            change = (1 / RATINGS.number)
        if value[0] == "-":
            change = -change
        rating = song("~#rating") + change
    else:
        try:
            rating = float(value)
        except (ValueError, TypeError):
            return
    song["~#rating"] = max(0.0, min(1.0, rating))
    app.library.changed([song])


@registry.register("dump-browsers")
def _dump_browsers(app):
    response = u""
    for i, b in enumerate(browsers.browsers):
        response += u"%d. %s\n" % (i, browsers.name(b))
    return text2fsn(response)


@registry.register("set-browser", args=1)
def _set_browser(app, value):
    if not app.window.select_browser(value, app.library, app.player):
        raise CommandError("Unknown browser %r" % value)


@registry.register("open-browser", args=1)
def _open_browser(app, value):
    value = arg2text(value)

    try:
        browser_cls = browsers.get(value)
    except ValueError as e:
        raise CommandError("Unknown browser %r" % value) from e
    LibraryBrowser.open(browser_cls, app.library, app.player)


@registry.register("random", args=1)
def _random(app, tag):
    tag = arg2text(tag)
    if app.browser.can_filter(tag):
        app.browser.filter_random(tag)


@registry.register("filter", args=1)
def _filter(app, value):
    value = arg2text(value)

    try:
        tag, value = value.split("=", 1)
    except ValueError as e:
        raise CommandError("invalid argument") from e

    if app.browser.can_filter(tag):
        app.browser.filter(tag, [value])


@registry.register("query", args=1)
def _query(app, value):
    value = arg2text(value)

    if app.browser.can_filter_text():
        app.browser.filter_text(value)


@registry.register("unfilter")
def _unfilter(app):
    app.browser.unfilter()


@registry.register("properties", optional=1)
def _properties(app, value=None):
    library = app.library
    player = app.player
    window = app.window

    if value is not None:
        value = arg2text(value)
        if value in library:
            songs = [library[value]]
        else:
            songs = library.query(value)
    else:
        songs = [player.song]

    songs = list(filter(None, songs))

    if songs:
        window = SongProperties(library, songs, parent=window)
        window.show()


@registry.register("enqueue", args=1)
def _enqueue(app, value):
    playlist = app.window.playlist
    library = app.library
    if value in library:
        songs = [library[value]]
    elif os.path.isfile(value):
        songs = [library.add_filename(os.path.realpath(value))]
    else:
        songs = library.query(arg2text(value))
    songs.sort()
    playlist.enqueue(songs)


@registry.register("enqueue-files", args=1)
def _enqueue_files(app, value):
    """Enqueues comma-separated filenames or song names.
    Commas in filenames should be backslash-escaped"""

    library = app.library
    window = app.window
    songs = []
    for param in split_escape(value, ","):
        try:
            song_path = uri2fsn(param)
        except ValueError:
            song_path = param
        if song_path in library:
            songs.append(library[song_path])
        elif os.path.isfile(song_path):
            songs.append(library.add_filename(os.path.realpath(value)))
    if songs:
        window.playlist.enqueue(songs)


@registry.register("unqueue", args=1)
def _unqueue(app, value):
    window = app.window
    library = app.library
    playlist = window.playlist
    if value in library:
        songs = [library[value]]
    else:
        songs = library.query(arg2text(value))
    playlist.unqueue(songs)


@registry.register("quit")
def _quit(app):
    app.quit()


@registry.register("status")
def _status(app):
    player = app.player

    if player.paused:
        strings = ["paused"]
    else:
        strings = ["playing"]
    strings.append(type(app.browser).__name__)
    po = app.player_options
    strings.append("%0.3f" % player.volume)
    strings.append("shuffle" if po.shuffle else "inorder")
    strings.append("on" if po.repeat else "off")
    progress = 0
    if player.info:
        length = player.info.get("~#length", 0)
        if length:
            progress = player.get_position() / (length * 1000.0)
    strings.append("%0.3f" % progress)
    status = u" ".join(strings) + u"\n"

    return text2fsn(status)


@registry.register("queue", args=1)
def _queue(app, value):
    window = app.window
    value = arg2text(value)

    if value.startswith("t"):
        value = not window.qexpander.get_property("visible")
    else:
        value = value not in ["0", "off", "false"]
    window.qexpander.set_property("visible", value)


@registry.register("dump-playlist", optional=1)
def _dump_playlist(app, fstring=None):
    pattern = make_pattern(fstring, "<~uri>")
    window = app.window
    items = []
    for song in window.playlist.pl.get():
        items.append(pattern.format(song))
    return text2fsn(u"\n".join(items) + u"\n")


@registry.register("dump-queue", optional=1)
def _dump_queue(app, fstring=None):
    pattern = make_pattern(fstring, "<~uri>")
    window = app.window
    items = []
    for song in window.playlist.q.get():
        items.append(pattern.format(song))
    return text2fsn(u"\n".join(items) + u"\n")


@registry.register("refresh")
def _refresh(app):
    scan_library(app.library, False)


@registry.register("print-query", args=1)
def _print_query(app, json_encoded_args):
    """Queries library, dumping filenames of matches to stdout
    See Issue 716
    """

    try:
        args = json.loads(arg2text(json_encoded_args))
        query = args["query"]
        fstring = args["pattern"]
    except (json.decoder.JSONDecodeError, KeyError, TypeError):
        # backward compatibility
        query = arg2text(json_encoded_args)
        fstring = None
    if (not isinstance(query, str)
        or (fstring is not None and not isinstance(fstring, str))):
        # This should not happen
        return "\n"
    pattern = make_pattern(fstring, "<~filename>")
    songs = app.library.query(query)
    return "\n".join([text2fsn(pattern.format(song)) for song in songs]) + "\n"


@registry.register("print-query-text")
def _print_query_text(app):
    if app.browser.can_filter_text():
        return text2fsn(str(app.browser.get_filter_text()) + u"\n")


@registry.register("print-playing", optional=1)
def _print_playing(app, fstring=None):
    from quodlibet.formats import AudioFile

    pattern = make_pattern(fstring, u"<artist~album~tracknumber~title>")
    song = app.player.info
    if song is None:
        song = AudioFile({"~filename": fsnative(u"/")})
        song.sanitize()
    else:
        song = app.player.with_elapsed_info(song)
    return text2fsn(pattern.format(song) + u"\n")


@registry.register("uri-received", args=1)
def _uri_received(app, uri):
    uri = arg2text(uri)
    app.browser.emit("uri-received", uri)
