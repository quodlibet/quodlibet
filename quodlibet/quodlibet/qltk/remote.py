# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna,
#           2011-2013 Nick Boultbee
#           2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import errno

from gi.repository import GLib

import quodlibet
from quodlibet import browsers

from quodlibet import const
from quodlibet import util
from quodlibet import qltk
from quodlibet.util.uri import URI

from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.properties import SongProperties
from quodlibet.util.library import scan_library
from quodlibet.util.path import mkdir


class FSInterface(object):
    """Provides a file in ~/.quodlibet to indicate what song is playing."""
    def __init__(self, player):
        player.connect('song-started', self.__started)
        player.connect('song-ended', self.__ended)

    def destroy(self):
        try:
            os.unlink(const.CURRENT)
        except EnvironmentError:
            pass

    def __started(self, player, song):
        if song:
            try:
                f = file(const.CURRENT, "w")
            except EnvironmentError:
                pass
            else:
                f.write(song.to_dump())
                f.close()

    def __ended(self, player, song, stopped):
        try:
            os.unlink(const.CURRENT)
        except EnvironmentError:
            pass


class _FIFO(object):
    """Creates and reads from a FIFO"""

    def __init__(self):
        self.__open(None)

    def handle_data(self, data):
        """Gets called with new read data"""

        raise NotImplementedError

    def destroy(self):
        if self._id is not None:
            GLib.source_remove(self._id)

        try:
            os.unlink(const.CONTROL)
        except EnvironmentError:
            pass

    def __open(self, *args):
        self._id = None
        try:
            if not os.path.exists(const.CONTROL):
                mkdir(const.USERDIR)
                os.mkfifo(const.CONTROL, 0600)
            fifo = os.open(const.CONTROL, os.O_NONBLOCK)
            f = os.fdopen(fifo, "r", 4096)
            self._id = qltk.io_add_watch(
                f, GLib.PRIORITY_DEFAULT,
                GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP,
                self.__process, *args)
        except (EnvironmentError, AttributeError):
            pass

    def __process(self, source, condition, *args):
        if condition in (GLib.IO_ERR, GLib.IO_HUP):
            self.__open(*args)
            return False

        while True:
            try:
                data = source.read()
            except (IOError, OSError) as e:
                if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return True
                elif e.errno == errno.EINTR:
                    continue
                else:
                    self.__open(*args)
                    return False
            break

        if not data:
            self.__open(*args)
            return False

        try:
            self.handle_data(data)
        except:
            util.print_exc()

        return True


class FIFOCommandError(Exception):
    pass


class FIFOControl(_FIFO):
    """A FIFO to control the player/library from."""

    _commands = {}

    def __init__(self, app):
        super(FIFOControl, self).__init__()
        self.app = app

    def handle_data(self, data):
        commands = data.rstrip("\n").splitlines()
        app = self.app

        for command in commands:
            # only one arg supported atm
            parts = command.split(" ", 1)
            cmd = parts[0]
            args = parts[1:]

            try:
                self.run(app, cmd, *args)
            except FIFOCommandError as e:
                print_e(str(e))
                continue
            except:
                util.print_exc()
                continue

    @classmethod
    def run(cls, app, name, *args):
        """Execute the command `name` passing args

        May raise FIFOCommandError
        """

        if name not in cls._commands:
            # browser commands
            commands = app.browser.commands
            if name in commands:
                if not args:
                    raise FIFOCommandError("Missing argument for %r" % name)
                cmd = commands[name]
                cmd(args[0], app.library, app.window, app.player)
                return
            else:
                raise FIFOCommandError("Unknown command %r" % name)

        cmd, argcount, optcount = cls._commands[name]
        if len(args) < argcount:
            raise FIFOCommandError("Not enough arguments for %r" % name)
        if len(args) > argcount + optcount:
            raise FIFOCommandError("Too many arguments for %r" % name)

        print_d("Running %r with params %r " % (cmd, args))

        try:
            cmd(app, *args)
        except FIFOCommandError as e:
            raise FIFOCommandError("%s: %s" % (name, str(e)))

    @classmethod
    def command(cls, name, args=0, optional=0):
        """Register a new command function"""

        def wrap(func):
            cls._commands[name] = (func, args, optional)
            return func
        return wrap


@FIFOControl.command("previous")
def _previous(app):
    app.player.previous()


@FIFOControl.command("force-previous")
def _force_previous(app):
    app.player.previous(True)


@FIFOControl.command("next")
def _next(app):
    app.player.next()


@FIFOControl.command("pause")
def _pause(app):
    app.player.paused = True


@FIFOControl.command("play")
def _play(app):
    player = app.player
    if player.song:
        player.paused = False


@FIFOControl.command("play-pause")
def _play_pause(app):
    player = app.player
    if player.song is None:
        player.reset()
    else:
        player.paused ^= True


@FIFOControl.command("stop")
def _stop(app):
    app.player.stop()


@FIFOControl.command("focus")
def _focus(app):
    app.present()


@FIFOControl.command("volume", args=1)
def _volume(app, value):
    if not value:
        raise FIFOCommandError("invalid arg")

    if value[0] in ('+', '-'):
        if len(value) > 1:
            try:
                change = (int(value[1:]) / 100.0)
            except ValueError:
                return
        else:
            change = 0.05
        if value[0] == '-':
            change = -change
        volume = app.player.volume + change
    else:
        try:
            volume = (int(value) / 100.0)
        except ValueError:
            return
    app.player.volume = min(1.0, max(0.0, volume))


@FIFOControl.command("order", args=1)
def _order(app, value):
    order = app.window.order

    try:
        order.set_active(
            ["inorder", "shuffle", "weighted", "onesong"].index(value))
    except ValueError:
        try:
            order.set_active(int(value))
        except (ValueError, TypeError):
            if value in ["t", "toggle"]:
                order.set_active(not order.get_active())


@FIFOControl.command("repeat", args=1)
def _repeat(app, value):
    repeat = app.window.repeat
    if value in ["0", "off"]:
        repeat.set_active(False)
    elif value in ["1", "on"]:
        repeat.set_active(True)
    elif value in ["t", "toggle"]:
        repeat.set_active(not repeat.get_active())


@FIFOControl.command("seek", args=1)
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


@FIFOControl.command("add-file", args=1)
def _add_file(app, value):
    filename = os.path.realpath(value)
    song = app.library.add_filename(filename)
    if song:
        playlist = app.window.playlist
        if song not in playlist.pl:
            queue = playlist.q
            queue.insert_before(queue.get_iter_first(), row=[song])
            app.player.next()
        else:
            app.player.go_to(app.library[filename])
            app.player.paused = False


@FIFOControl.command("add-directory", args=1)
def _add_directory(app, value):
    player = app.player
    window = app.window
    library = app.library
    filename = os.path.normpath(os.path.realpath(value))
    for added in library.scan([filename]):
        pass
    if app.browser.can_filter_text():
        app.browser.filter_text(
            "filename = /^%s/c" % re.escape(filename))
    else:
        basepath = filename + "/"
        songs = [song for (fn, song) in library.iteritems()
                 if fn.startswith(basepath)]
        songs.sort(reverse=True)
        queue = window.playlist.q
        for song in songs:
            queue.insert_before(queue.get_iter_first(), row=[song])
    player.next()


@FIFOControl.command("toggle-window")
def _toggle_window(app):
    if app.window.get_property('visible'):
        app.hide()
    else:
        app.show()


@FIFOControl.command("hide-window")
def _hide_window(app):
    app.hide()


@FIFOControl.command("show-window")
def _show_window(app):
    app.show()


@FIFOControl.command("set-rating", args=1)
def _set_rating(app, value):
    song = app.player.song
    if not song:
        return

    try:
        song["~#rating"] = max(0.0, min(1.0, float(value)))
    except (ValueError, TypeError):
        pass
    else:
        app.library.changed([song])


@FIFOControl.command("dump-browsers", args=1)
def _dump_browsers(app, value):
    try:
        f = file(value, "w")
    except EnvironmentError:
        pass
    else:
        for i, browser in enumerate(browsers.browsers):
            if browser is not browsers.empty.EmptyBar:
                f.write("%d. %s\n" % (i, browser.__name__))
        f.close()


@FIFOControl.command("set-browser", args=1)
def _set_browser(app, value):
    Kind = browsers.get(value)
    if Kind is not browsers.empty.EmptyBar:
        app.window.select_browser(None, value, app.library, app.player)
    else:
        raise FIFOCommandError("Unknown browser %r" % value)


@FIFOControl.command("open-browser", args=1)
def _open_browser(app, value):
    Kind = browsers.get(value)
    if Kind is not browsers.empty.EmptyBar:
        LibraryBrowser.open(Kind, app.library)
    else:
        raise FIFOCommandError("Unknown browser %r" % value)


@FIFOControl.command("random", args=1)
def _random(app, tag):
    if app.browser.can_filter(tag):
        app.browser.filter_random(tag)


@FIFOControl.command("filter", args=1)
def _filter(app, value):
    try:
        tag, values = value.split('=', 1)
        values = [v.decode("utf-8", "replace") for v in values.split("\x00")]
    except ValueError:
        raise FIFOCommandError("invalid argument")
    if app.browser.can_filter(tag) and values:
        app.browser.filter(tag, values)


@FIFOControl.command("unfilter")
def _unfilter(app):
    app.browser.unfilter()


@FIFOControl.command("properties", optional=1)
def _properties(app, value=None):
    library = app.library
    player = app.player
    window = app.window

    if value:
        if value in library:
            songs = [library[value]]
        else:
            songs = library.query(value)
    else:
        songs = [player.song]
    songs = filter(None, songs)

    if songs:
        window = SongProperties(library, songs, parent=window)
        window.show()


@FIFOControl.command("enqueue", args=1)
def _enqueue(app, value):
    playlist = app.window.playlist
    library = app.library
    if value in library:
        songs = [library[value]]
    elif os.path.isfile(value):
        songs = [library.add_filename(os.path.realpath(value))]
    else:
        songs = library.query(value)
    songs.sort()
    playlist.enqueue(songs)


@FIFOControl.command("enqueue-files", args=1)
def _enqueue_files(app, value):
    """Enqueues comma-separated filenames or song names."""

    library = app.library
    window = app.window
    songs = []
    for param in value.split(","):
        try:
            song_path = URI(param).filename
        except ValueError:
            song_path = param
        if song_path in library:
            songs.append(library[song_path])
        elif os.path.isfile(song_path):
            songs.append(library.add_filename(os.path.realpath(value)))
    if songs:
        window.playlist.enqueue(songs)


@FIFOControl.command("unqueue", args=1)
def _unqueue(app, value):
    window = app.window
    library = app.library
    playlist = window.playlist
    if value in library:
        songs = [library[value]]
    else:
        songs = library.query(value)
    playlist.unqueue(songs)


@FIFOControl.command("quit")
def _quit(app):
    app.quit()


@FIFOControl.command("status", args=1)
def _status(app, value):
    player = app.player
    window = app.window

    try:
        f = file(value, "w")
    except EnvironmentError:
        pass
    else:
        if player.paused:
            strings = ["paused"]
        else:
            strings = ["playing"]
        strings.append(type(app.browser).__name__)
        strings.append("%0.3f" % player.volume)
        strings.append(window.order.get_active_name())
        strings.append((window.repeat.get_active() and "on") or "off")
        progress = 0
        if player.info:
            length = player.info.get("~#length", 0)
            if length:
                progress = player.get_position() / (length * 1000.0)
        strings.append("%0.3f" % progress)
        f.write(" ".join(strings) + "\n")
        try:
            f.write(app.browser.status + "\n")
        except AttributeError:
            pass
        f.close()


@FIFOControl.command("song-list", args=1)
def _song_list(app, value):
    window = app.window
    if value.startswith("t"):
        value = not window.song_scroller.get_property('visible')
    else:
        value = value not in ['0', 'off', 'false']
    window.song_scroller.set_property('visible', value)


@FIFOControl.command("queue", args=1)
def _queue(app, value):
    window = app.window
    if value.startswith("t"):
        value = not window.qexpander.get_property('visible')
    else:
        value = value not in ['0', 'off', 'false']
    window.qexpander.set_property('visible', value)


@FIFOControl.command("dump-playlist", args=1)
def _dump_playlist(app, value):
    window = app.window

    try:
        f = file(value, "w")
    except EnvironmentError:
        pass
    else:
        for song in window.playlist.pl.get():
            f.write(song("~uri") + "\n")
        f.close()


@FIFOControl.command("dump-queue", args=1)
def _dump_queue(app, value):
    window = app.window
    try:
        f = file(value, "w")
    except EnvironmentError:
        pass
    else:
        for song in window.playlist.q.get():
            f.write(song("~uri") + "\n")
        f.close()


@FIFOControl.command("refresh")
def _refresh(app):
    scan_library(app.library, False)
