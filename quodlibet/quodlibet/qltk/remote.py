# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import sys

import gobject
import gtk

from quodlibet import browsers
from quodlibet import config
from quodlibet import const
from quodlibet import util
from quodlibet.util.uri import URI

from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.properties import SongProperties
from quodlibet.util import copool

class FSInterface(object):
    """Provides a file in ~/.quodlibet to indicate what song is playing."""
    def __init__(self, player):
        player.connect('song-started', self.__started)
        player.connect('song-ended', self.__ended)
        gtk.quit_add(1, self.__cleanup)

    def __cleanup(self):
        try: os.unlink(const.CURRENT)
        except EnvironmentError: pass

    def __started(self, player, song):
        if song:
            try: f = file(const.CURRENT, "w")
            except EnvironmentError: pass
            else:
                f.write(song.to_dump())
                f.close()

    def __ended(self, player, song, stopped):
        try: os.unlink(const.CURRENT)
        except EnvironmentError: pass

class FIFOControl(object):
    """A FIFO to control the player/library from."""

    def __init__(self, library, window, player):
        self.__open(library, window, player)
        gtk.quit_add(1, self.__cleanup)

    def __cleanup(self):
        try: os.unlink(const.CONTROL)
        except EnvironmentError: pass

    def __open(self, *args):
        try:
            if not os.path.exists(const.CONTROL):
                util.mkdir(const.USERDIR)
                os.mkfifo(const.CONTROL, 0600)
            fifo = os.open(const.CONTROL, os.O_NONBLOCK)
            f = os.fdopen(fifo, "r", 4096)
            gobject.io_add_watch(
                f, gtk.gdk.INPUT_READ, self.__process, *args)
        except (EnvironmentError, AttributeError): pass

    def __getitem__(self, key):
        key = key.replace("-", "_")
        if key.startswith("_"): raise ValueError
        else:
            try: return getattr(self, "_"+key)
            except AttributeError: raise KeyError, key

    def __process(self, source, condition, *args):
        commands = source.read().rstrip("\n").splitlines()
        if commands == []:
            self.__open(*args)
            return False
        else:
            for command in commands:
                try:
                    try: cmd, arg = command.split(' ', 1)
                    except ValueError: self[command](*args)
                    else:
                        print_d("Running %r with params %r " % (cmd, arg))
                        self[cmd](arg, *args)
                except KeyError:
                    commands = args[1].browser.commands
                    try:
                        try: cmd, arg = command.split(' ', 1)
                        except ValueError: commands[command](*args)
                        else: commands[cmd](arg, *args)
                    except:
                        print_w(_("Invalid command %r received.") % command)
                except:
                    e = sys.exc_info()[1]
                    print_e(_("Error running command %r, caused by: %r.") %
                        (command, e))
            return True

    def _previous(self, library, window, player): player.previous()
    def _force_previous(self, library, window, player): player.previous(True)
    def _next(self, library, window, player): player.next()
    def _pause(self, library, window, player): player.paused = True
    def _play(self, library, window, player):
        if player.song: player.paused = False
    def _play_pause(self, library, window, player):
        if player.song is None:
            player.reset()
        else: player.paused ^= True

    def _stop(self, library, window, player):
        player.stop()

    def _focus(self, library, window, player):
        from quodlibet import app
        app.present()

    def _volume(self, value, library, window, player):
        if value[0] in ('+', '-'):
            if len(value) > 1:
                try: change = (int(value[1:]) / 100.0)
                except ValueError: return
            else:
                change = 0.05
            if value[0] == '-': change = -change
            volume = player.volume + change
        else:
            try: volume = (int(value) / 100.0)
            except ValueError: return
        player.volume = min(1.0, max(0.0, volume))

    def _order(self, value, library, window, player):
        order = window.order
        try:
            order.set_active(
                ["inorder", "shuffle", "weighted", "onesong"].index(value))
        except ValueError:
            try: order.set_active(int(value))
            except (ValueError, TypeError):
                if value in ["t", "toggle"]:
                    order.set_active(not order.get_active())

    def _repeat(self, value, library, window, player):
        repeat = window.repeat
        if value in ["0", "off"]: repeat.set_active(False)
        elif value in ["1", "on"]: repeat.set_active(True)
        elif value in ["t", "toggle"]:
            repeat.set_active(not repeat.get_active())

    def _seek(self, time, library, window, player):
        seek_to = player.get_position()
        if time[0] == "+": seek_to += util.parse_time(time[1:]) * 1000
        elif time[0] == "-": seek_to -= util.parse_time(time[1:]) * 1000
        else: seek_to = util.parse_time(time) * 1000
        seek_to = min(player.song.get("~#length", 0) * 1000 -1,
                      max(0, seek_to))
        player.seek(seek_to)

    def _add_file(self, value, library, window, player):
        filename = os.path.realpath(value)
        song = library.add_filename(filename)
        if song:
            if song not in window.playlist.pl:
                queue = window.playlist.q
                queue.insert_before(queue.get_iter_first(), row=[song])
                player.next()
            else:
                player.go_to(library[filename])
                player.paused = False

    def _add_directory(self, value, library, window, player):
        filename = os.path.normpath(os.path.realpath(value))
        for added in library.scan([filename]): pass
        if window.browser.can_filter_text():
            window.browser.filter_text(
                "filename = /^%s/c" % re.escape(filename))
        else:
            basepath = filename + "/"
            songs = [song for (filename, song) in library.iteritems()
                     if filename.startswith(basepath)]
            songs.sort(reverse=True)
            queue = window.playlist.q
            for song in songs:
                queue.insert_before(queue.get_iter_first(), row=[song])
        player.next()

    def _toggle_window(self, library, window, player):
        from quodlibet import app
        if window.get_property('visible'):
            app.hide()
        else:
            app.show()

    def _hide_window(self, library, window, player):
        from quodlibet import app
        app.hide()

    def _show_window(self, library, window, player):
        from quodlibet import app
        app.show()

    def _set_rating(self, value, library, window, player):
        song = player.song
        if song:
            try: song["~#rating"] = max(0.0, min(1.0, float(value)))
            except (ValueError, TypeError): pass
            else: library.changed([song])

    def _set_browser(self, value, library, window, player):
        Kind = browsers.get(value)
        if Kind is not browsers.search.EmptyBar:
            window.select_browser(None, value, library, player)
        else: print_w(_("Unknown browser %r.") % value)

    def _open_browser(self, value, library, window, player):
        Kind = browsers.get(value)
        if Kind is not browsers.search.EmptyBar:
            LibraryBrowser(Kind, library)
        else: print_w(_("Unknown browser %r.") % value)

    def _random(self, tag, library, window, player):
        if window.browser.can_filter(tag):
            window.browser.filter_random(tag)

    def _filter(self, value, library, window, player):
        tag, values = value.split('=', 1)
        values = [v.decode("utf-8", "replace") for v in values.split("\x00")]
        if window.browser.can_filter(tag) and values:
            window.browser.filter(tag, values)

    def _unfilter(self, library, window, player):
        window.browser.unfilter()

    def _properties(self, value, library, window, player=None):
        if player is None:
            # no value given, use the current song; slide arguments
            # to the right.
            value, library, window, player = None, value, library, window

        if value:
            if value in library:
                songs = [library[value]]
            else:
                songs = library.query(value)
        else:
            songs = [player.song]
        songs = filter(None, songs)

        if songs:
            SongProperties(library, songs, parent=window)

    def _enqueue(self, value, library, window, player):
        playlist = window.playlist
        if value in library: songs = [library[value]]
        elif os.path.isfile(value):
            songs = [library.add_filename(os.path.realpath(value))]
        else: songs = library.query(value)
        songs.sort()
        playlist.enqueue(songs)

    def _enqueue_files(self, value, library, window, player):
        '''Enqueues comma-separated filenames or song names

            See Issue 716
        '''
        songs = []
        for param in value.split(","):
            try:
                song_path = URI(param).filename
            except ValueError:
                song_path = param
            if song_path in library: songs.append(library[song_path])
            elif os.path.isfile(song_path):
                songs.append(library.add_filename(os.path.realpath(value)))
        if songs: window.playlist.enqueue(songs)

    def _unqueue(self, value, library, window, player):
        playlist = window.playlist
        if value in library: songs = [library[value]]
        else: songs = library.query(value)
        playlist.unqueue(songs)

    def _quit(self, library, window, player):
        from quodlibet import app
        app.quit()

    def _status(self, value, library, window, player):
        try: f = file(value, "w")
        except EnvironmentError: pass
        else:
            if player.paused: strings = ["paused"]
            else: strings = ["playing"]
            strings.append(type(window.browser).__name__)
            strings.append("%0.3f" % player.volume)
            strings.append(window.order.get_active_name())
            strings.append((window.repeat.get_active() and "on") or "off")
            progress = 0
            if player.info:
                length = player.info.get("~#length", 0)
                if length: progress = player.get_position() / (length * 1000.0)
            strings.append("%0.3f" % progress)
            f.write(" ".join(strings) + "\n")
            try: f.write(window.browser.status + "\n")
            except AttributeError: pass
            f.close()

    def _song_list(self, value, library, window, player):
        if value.startswith("t"):
            value = not window.song_scroller.get_property('visible')
        else: value = value not in ['0', 'off', 'false']
        window.song_scroller.set_property('visible', value)

    def _queue(self, value, library, window, player):
        if value.startswith("t"):
            value = not window.qexpander.get_property('visible')
        else: value = value not in ['0', 'off', 'false']
        window.qexpander.set_property('visible', value)

    def _dump_playlist(self, value, library, window, player):
        try: f = file(value, "w")
        except EnvironmentError: pass
        else:
            for song in window.playlist.pl.get():
                f.write(song("~uri") + "\n")
            f.close()

    def _dump_queue(self, value, library, window, player):
        try: f = file(value, "w")
        except EnvironmentError: pass
        else:
            for song in window.playlist.q.get():
                f.write(song("~uri") + "\n")
            f.close()

    def _refresh(self, library, window, player):
        paths = util.split_scan_dirs(config.get("settings", "scan"))
        progress = window.statusbar.progress
        copool.add(library.rebuild, paths, progress, False, funcid="library")
