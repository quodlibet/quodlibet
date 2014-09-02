#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012,2013 Christoph Reiter
#           2010-2014 Nick Boultbee
# <quod-libet-development@googlegroups.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import sys
import os
from quodlibet.cli import process_arguments, is_running, control
from quodlibet.util.dprint import print_d, print_


def main():
    startup_actions = process_arguments()

    from quodlibet import const
    if is_running() and not const.DEBUG:
        print_(_("Quod Libet is already running."))
        control('focus')

    import quodlibet
    from quodlibet import app
    from quodlibet.qltk import add_signal_watch
    add_signal_watch(app.quit)

    import quodlibet.player
    from quodlibet import config
    from quodlibet import browsers
    from quodlibet import const
    from quodlibet import util

    config.init(const.CONFIG)

    library = quodlibet.init(library=const.LIBRARY,
                             icon="quodlibet",
                             name="Quod Libet",
                             title=const.PROCESS_TITLE_QL)
    app.library = library

    from quodlibet.player import PlayerError
    # this assumes that nullbe will always succeed
    for backend in [config.get("player", "backend"), "nullbe"]:
        try:
            player = quodlibet.init_backend(backend, app.librarian)
        except PlayerError as error:
            print_e("%s. %s" % (error.short_desc, error.long_desc))
        else:
            break
    app.player = player

    os.environ["PULSE_PROP_media.role"] = "music"
    os.environ["PULSE_PROP_application.icon_name"] = "quodlibet"

    browsers.init()

    from quodlibet.qltk.songlist import SongList, get_columns

    from quodlibet.util.collection import Album
    try:
        cover_size = config.getint("browsers", "cover_size")
    except config.Error:
        pass
    else:
        if cover_size > 0:
            Album.COVER_SIZE = cover_size

    headers = get_columns()
    SongList.set_all_column_headers(headers)

    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        util.tags.add(opt, val)

    in_all = ("~filename ~uri ~#lastplayed ~#rating ~#playcount ~#skipcount "
              "~#added ~#bitrate ~current ~#laststarted ~basename "
              "~dirname").split()
    for Kind in browsers.browsers:
        if Kind.headers is not None:
            Kind.headers.extend(in_all)
        Kind.init(library)

    pm = quodlibet.init_plugins("no-plugins" in startup_actions)

    if hasattr(player, "init_plugins"):
        player.init_plugins()

    from quodlibet.qltk import unity
    unity.init("quodlibet.desktop", player)

    from quodlibet.qltk.songsmenu import SongsMenu
    SongsMenu.init_plugins()
    from quodlibet.util.cover.manager import cover_plugins
    cover_plugins.init_plugins()
    from quodlibet.plugins.playlist import PLAYLIST_HANDLER
    PLAYLIST_HANDLER.init_plugins()

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
    fsiface = FSInterface(player)
    quodlibet.quit_add(1, fsiface.destroy)

    fifoctrl = FIFOControl(app)
    quodlibet.quit_add(1, fifoctrl.destroy)

    DBusHandler(player, library)
    SongTracker(library.librarian, player, window.playlist)

    from quodlibet.qltk import session
    session.init("quodlibet")

    quodlibet.enable_periodic_save(save_library=True)

    if "start-playing" in startup_actions:
        player.paused = False

    # restore browser windows
    from quodlibet.qltk.browser import LibraryBrowser
    from gi.repository import GLib
    GLib.idle_add(LibraryBrowser.restore, library, priority=GLib.PRIORITY_HIGH)

    quodlibet.main(window)

    print_d("Shutting down player device %r." % player.version_info)
    player.destroy()
    quodlibet.library.save(force=True)

    config.save(const.CONFIG)

    print_d("Finished shutdown.")


if __name__ == "__main__":
    main()
