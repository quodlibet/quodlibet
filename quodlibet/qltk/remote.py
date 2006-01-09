# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import sre
import gobject, gtk
import browsers
import const
import util

from qltk.browser import LibraryBrowser

class FSInterface(object):
    """Provides a file in ~/.quodlibet to indicate what song is playing."""
    def __init__(self, watcher):
        watcher.connect('song-started', self.__started)
        watcher.connect('song-ended', self.__ended)

    def __started(self, watcher, song):
        if song:
            try: f = file(const.CURRENT, "w")
            except EnvironmentError: pass
            else:
                f.write(song.to_dump())
                f.close()

    def __ended(self, watcher, song, stopped):
        try: os.unlink(const.CURRENT)
        except EnvironmentError: pass

class FIFOControl(object):
    """A FIFO to control the player/library from."""

    def __init__(self, watcher, window, player):
        from plugins.remote import RemotePlugins
        self.plugins = RemotePlugins()
        self.__open(watcher, window, player)

    def __open(self, *args):
        self.plugins.rescan()
        try:
            if not os.path.exists(const.CONTROL):
                util.mkdir(const.DIR)
                os.mkfifo(const.CONTROL, 0600)
            fifo = os.open(const.CONTROL, os.O_NONBLOCK)
            f = os.fdopen(fifo, "r", 4096)
            gobject.io_add_watch(
                f, gtk.gdk.INPUT_READ, self.__process, *args)
        except EnvironmentError: pass

    def __getitem__(self, key):
        key = key.replace("-", "_")
        if key.startswith("_"): raise ValueError
        else:
            try: return getattr(self, "_"+key)
            except AttributeError: raise KeyError, key

    def __process(self, source, condition, *args):
        command = source.read().rstrip("\n")
        if command == "":
            self.__open(*args)
            return False
        else:
            try:
                try: cmd, arg = command.split(' ', 1)
                except: self[command](*args)
                else: self[cmd](arg, *args)
            except KeyError:
                try: cmd, arg = command.split(' ', 1)
                except:
                    for Plugin in self.plugins.FIFOPlugins():
                        if command in Plugin.commands:
                            try: Plugin(command, *args)
                            except: import traceback; traceback.print_exc()
                            break
                    else: print "W: Invalid command %s received." % command
                else:
                    for Plugin in self.plugins.FIFOPlugins():
                        if cmd in Plugin.commands:
                            try: Plugin(cmd, arg, *args)
                            except: import traceback; traceback.print_exc()
                            break
                    else: print "W: Invalid command %s received." % command
            return True

    def _previous(self, watcher, window, player): player.previous()
    def _next(self, watcher, window, player): player.next()
    def _pause(self, watcher, window, player): player.paused = True
    def _play(self, watcher, window, player):
        if player.song: player.paused = False
    def _play_pause(self, watcher, window, player):
        if player.song is None:
            player.reset()
            player.next()
        else: player.paused ^= True

    def _focus(self, watcher, window, player): window.present()

    def _volume(self, value, watcher, window, player):
        if value[0] == "+": window.volume += 0.05
        elif value == "-": window.volume -= 0.05
        else:
            try: window.volume.set_value(int(value) / 100.0)
            except ValueError: pass

    def _order(self, value, watcher, window, player):
        order = window.order
        try:
            order.set_active(
                ["inorder", "shuffle", "weighted", "onesong"].index(value))
        except ValueError:
            try: order.set_active(int(value))
            except (ValueError, TypeError):
                if value in ["t", "toggle"]:
                    order.set_active(not order.get_active())

    def _repeat(self, value, watcher, window, player):
        repeat = window.repeat
        if value in ["0", "off"]: repeat.set_active(False)
        elif value in ["1", "on"]: repeat.set_active(True)
        elif value in ["t", "toggle"]:
            repeat.set_active(not repeat.get_active())

    def _query(self, value, watcher, window, player):
        if window.browser.can_filter(None):
            window.browser.set_text(value)
            window.browser.activate()

    def _seek(self, time, watcher, window, player):
        seek_to = player.get_position()
        if time[0] == "+": seek_to += util.parse_time(time[1:]) * 1000
        elif time[0] == "-": seek_to -= util.parse_time(time[1:]) * 1000
        else: seek_to = util.parse_time(time) * 1000
        seek_to = min(player.song.get("~#length", 0) * 1000 -1,
                      max(0, seek_to))
        player.seek(seek_to)

    def _add_file(self, value, watcher, window, player):
        from library import library
        filename = os.path.realpath(value)
        song = library.add(filename)
        if song:
            if song != True: watcher.added([song])
            else: song = library[filename]
            if (song not in window.playlist.pl
                and window.browser.can_filter("filename")):
                window.browser.filter(
                    "filename", [filename])
            player.go_to(library[filename])
            player.paused = False

    def _add_directory(self, value, watcher, window, player):
        from library import library
        filename = os.path.realpath(value)
        for added, changed, removed in library.scan([filename]): pass
        if added: watcher.added(added)
        if changed: watcher.changed(changed)
        if removed: watcher.removed(removed)
        if added or changed or removed: watcher.refresh()
        if window.browser.can_filter(None):
            window.browser.set_text(
                "filename = /^%s/c" % sre.escape(filename))
            window.browser.activate()
            player.next()

    def _toggle_window(self, watcher, window, player):
        if window.get_property('visible'): window.hide()
        else: window.present()

    def _set_rating(self, value, watcher, window, player):
        song = player.song
        if song:
            try: song["~#rating"] = max(0.0, min(1.0, float(value)))
            except (ValueError, TypeError): pass
            else: watcher.changed([song])

    def _set_browser(self, value, watcher, window, player):
        Kind = browsers.get(value)
        if Kind is not browsers.search.EmptyBar:
            window.select_browser(None, Kind, player)
        else: print "W: Unknown browser type %r." % value

    def _open_browser(self, value, watcher, window, player):
        Kind = browsers.get(value)
        if Kind is not browsers.search.EmptyBar:
            LibraryBrowser(Kind, watcher)
        else: print "W: Unknown browser type %r." % value

    def _random(self, tag, watcher, window, player):
        if window.browser.can_filter(tag):
            from library import library
            value = library.random(tag)
            if value: window.browser.filter(tag, [value])

    def _filter(self, value, watcher, window, player):
        tag, values = value.split('=', 1)
        values = [v.decode("utf-8", "replace") for v in values.split("\x00")]
        if window.browser.can_filter(tag) and values:
            window.browser.filter(tag, values)

    def _properties(self, value, watcher, window, player=None):
        if player is None:
            # no value given, use the current song; slide arguments
            # to the right.
            value, watcher, window, player = None, value, watcher, window
        from qltk.properties import SongProperties
        if value:
            from library import library
            if value in library: songs = [library[value]]
            else: songs = library.query(value)
            SongProperties(songs, watcher, 0)
        else: SongProperties([player.song], watcher)

    def _enqueue(self, value, watcher, window, player):
        from library import library
        playlist = window.playlist
        if value in library: songs = [library[value]]
        else: songs = library.query(value)
        playlist.enqueue(songs)

    def _quit(self, watcher, window, player):
        window.destroy()

    def _status(self, value, watcher, window, player):
        try: f = file(value, "w")
        except EnvironmentError: pass
        else:
            if player.paused: strings = ["paused"]
            else: strings = ["playing"]
            strings.append(type(window.browser).__name__)
            strings.append("%0.3f" % window.volume.get_value())
            strings.append(window.order.get_active_name())
            strings.append((window.repeat.get_active() and "on") or "off")
            f.write(" ".join(strings) + "\n")
            try: f.write(window.browser.status + "\n")
            except AttributeError: pass
            f.close()

    def _song_list(self, value, watcher, window, player):
        if value.startswith("t"):
            value = not window.song_scroller.get_property('visible')
        else: value = value not in ['0', 'off', 'false']
        window.songlist.set_property('visible', value)

    def _queue(self, value, watcher, window, player):
        if value.startswith("t"):
            value = not window.qexpander.get_property('visible')
        else: value = value not in ['0', 'off', 'false']
        window.qexpander.set_property('visible', value)

    def _dump_playlist(self, value, watcher, window, player):
        try: f = file(value, "w")
        except EnvironmentError: pass
        else:
            for song in window.playlist.pl.get():
                f.write(song("~uri") + "\n")
            f.close()

    def _dump_queue(self, value, watcher, window, player):
        try: f = file(value, "w")
        except EnvironmentError: pass
        else:
            for song in window.playlist.q.get():
                f.write(song("~uri") + "\n")
            f.close()
