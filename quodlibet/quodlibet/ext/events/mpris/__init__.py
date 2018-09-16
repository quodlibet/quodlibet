# -*- coding: utf-8 -*-
# Copyright 2010,2012 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

from gi.repository import Gtk

import dbus

try:
    import indicate
except ImportError:
    indicate = None

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet import qltk
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk import Icons
from quodlibet.plugins.events import EventPlugin

from .mpris1 import MPRIS1Root, MPRIS1DummyTracklist, MPRIS1Player
from .mpris2 import MPRIS2


class MPRIS(EventPlugin):
    PLUGIN_ID = "mpris"
    PLUGIN_NAME = _("MPRIS D-Bus Support")
    PLUGIN_DESC = _("Allows control of Quod Libet using the "
                    "MPRIS 1.0/2.0 D-Bus Interface Specification.")
    PLUGIN_ICON = Icons.NETWORK_WORKGROUP

    def PluginPreferences(self, parent):
        box = Gtk.HBox()
        ccb = ConfigCheckButton(_("Hide main window on close"),
                                'plugins', 'mpris_window_hide')
        ccb.set_active(self.__do_hide())
        box.pack_start(qltk.Frame(_("Preferences"), child=ccb), True, True, 0)
        return box

    def __do_hide(self):
        return config.getboolean('plugins', 'mpris_window_hide', False)

    def __window_delete(self, win, event):
        if self.__do_hide():
            win.hide()
            return True

    def enabled(self):
        self.__sig = app.window.connect('delete-event', self.__window_delete)

        self.objects = []
        for service in [MPRIS1Root, MPRIS1DummyTracklist,
                        MPRIS1Player, MPRIS2]:
            try:
                self.objects.append(service())
            except dbus.DBusException:
                pass

        # Needed for sound menu support in some older Ubuntu versions
        if indicate:
            self.__indicate_server = s = indicate.indicate_server_ref_default()
            s.set_type("music.quodlibet")
            s.set_desktop_file(
                "/usr/share/applications/io.github.quodlibet.QuodLibet.desktop"
            )
            s.show()

    def disabled(self):
        if indicate:
            self.__indicate_server.hide()

        for obj in self.objects:
            obj.remove_from_connection()
        self.objects = []

        import gc
        gc.collect()

        app.window.disconnect(self.__sig)

    def plugin_on_paused(self):
        for obj in self.objects:
            obj.paused()

    def plugin_on_unpaused(self):
        for obj in self.objects:
            obj.unpaused()

    def plugin_on_song_started(self, song):
        for obj in self.objects:
            obj.song_started(song)

    def plugin_on_song_ended(self, song, skipped):
        for obj in self.objects:
            obj.song_ended(song, skipped)
