# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gtk
import stock

import browsers
import const
import config
import player
import util

from util import to
from library import library

from qltk.songlist import SongList
from qltk.msg import ErrorMessage

# FIXME: This is now deprecated in favor of the global main and
# watcher variables, removing the "widgets.widgets" problem.
class __widgets(object):
    __slots__ = ["watcher", "main"]
widgets = __widgets()

global main, watcher
main = watcher = None

def website_wrap(activator, link):
    if not util.website(link):
        ErrorMessage(
            main, _("Unable to start web browser"),
            _("A web browser could not be found. Please set "
              "your $BROWSER variable, or make sure "
              "/usr/bin/sensible-browser exists.")).run()

def init():
    global main, watcher

    stock.init()

    try:
        pb = gtk.gdk.pixbuf_new_from_file_at_size("quodlibet.svg", 64, 64)
        gtk.window_set_default_icon(pb)
    except: gtk.window_set_default_icon_from_file("quodlibet.png")

    if config.get("settings", "headers").split() == []:
       config.set("settings", "headers", "title")
    headers = config.get("settings", "headers").split()
    SongList.set_all_column_headers(headers)
            
    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        util.HEADERS_FILTER[opt] = val

    from qltk.watcher import SongWatcher
    watcher = widgets.watcher = SongWatcher()

    # plugin support
    from plugins import PluginManager
    SongList.pm = PluginManager(watcher, ["./plugins", const.PLUGINS])
    SongList.pm.rescan()

    in_all =("~filename ~uri ~#lastplayed ~#rating ~#playcount ~#skipcount "
             "~#added ~#bitrate ~current ~#laststarted").split()
    for Kind in zip(*browsers.browsers)[2]:
        if Kind.headers is not None: Kind.headers.extend(in_all)
        Kind.init(watcher)

    from qltk.quodlibet import QuodLibetWindow
    main = widgets.main = QuodLibetWindow(watcher)
    gtk.about_dialog_set_url_hook(website_wrap)

    # These stay alive in the watcher/other callbacks.
    from qltk.remote import FSInterface, FIFOControl
    FSInterface(watcher)
    FIFOControl(watcher, main, player.playlist)

    from qltk.count import CountManager
    CountManager(watcher, main.playlist)

    from qltk.trayicon import TrayIcon
    TrayIcon(watcher, main, player.playlist)

    flag = main.songlist.get_columns()[-1].get_clickable
    while not flag(): gtk.main_iteration()
    song = library.get(config.get("memory", "song"))
    player.playlist.setup(watcher, main.playlist, song)
    main.show()
    return main

def save_library(window, player):
    player.quit()

    # If something goes wrong here, it'll probably be caught
    # saving the library anyway.
    try: config.write(const.CONFIG)
    except EnvironmentError, err: pass

    for fn in [const.CONTROL, const.PAUSED, const.CURRENT]:
        # FIXME: PAUSED and CURRENT should be handled by
        # FSInterface.
        try: os.unlink(fn)
        except EnvironmentError: pass

    window.destroy()

    print to(_("Saving library."))
    try: library.save(const.LIBRARY)
    except EnvironmentError, err:
        err = str(err).decode('utf-8', 'replace')
        ErrorMessage(None, _("Unable to save library"), err).run()

def no_sink_quit(sink):
    header = _("Unable to open audio device")
    body = _("Quod Libet tried to access the 'alsasink', 'osssink', and "
             "'%(sink)s' drivers but could not open any of them. Set your "
             "GStreamer pipeline by changing the\n"
             "    <b>pipeline = %(sink)s</b>\n"
             "line in ~/.quodlibet/config.") % {"sink": sink}
    ErrorMessage(None, header, body).run()
    gtk.main_quit()

def no_source_quit():
    header = _("Unable to open files")
    body = _("Quod Libet could not find the 'filesrc' GStreamer element. "
             "Check your GStreamer installation.")
    ErrorMessage(None, header, body).run()
    gtk.main_quit()
