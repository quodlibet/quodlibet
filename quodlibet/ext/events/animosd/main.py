# Copyright (c) 2012,2013,2016 Nick Boultbee
# Copyright (C) 2012-13 Thomas Vogt
# Copyright (C) 2008 Andreas Bombe
# Copyright (C) 2005  Michael Urman
# Based on osd.py (C) 2005 Ton van den Heuvel, Joe Wreshnig
#                 (C) 2004 Gustavo J. A. M. Carneiro
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gdk, GLib

from quodlibet import _
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons
from quodlibet.util import cached_property

from .osdwindow import OSDWindow
from .config import get_config
from .prefs import AnimOsdPrefs


class AnimOsd(EventPlugin):
    PLUGIN_ID = "Animated On-Screen Display"
    PLUGIN_NAME = _("Animated On-Screen Display")
    PLUGIN_DESC = _("Displays song information on your screen when it " "changes.")
    PLUGIN_ICON = Icons.DIALOG_INFORMATION

    __current_window = None

    @cached_property
    def Conf(self):
        return get_config("animosd")

    def PluginPreferences(self, parent):
        return AnimOsdPrefs(self)

    def plugin_on_song_started(self, song):
        if self.__current_window is not None:
            if self.__current_window.is_composited():
                self.__current_window.fade_out()
            else:
                self.__current_window.hide()
                self.__current_window.destroy()

        if song is None:
            self.__current_window = None
            return

        window = OSDWindow(self.Conf, song)
        window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        window.connect("button-press-event", self.__buttonpress)
        window.connect("fade-finished", self.__fade_finished)
        self.__current_window = window

        window.set_opacity(0.0)
        window.show()
        window.fade_in()

    def plugin_on_error(self, song, error):
        if self.__current_window is not None:
            self.__current_window.destroy()
            self.__current_window = None

    @staticmethod
    def start_fade_out(window):
        window.fade_out()
        return False

    def __buttonpress(self, window, event):
        window.hide()
        if self.__current_window is window:
            self.__current_window = None
        window.destroy()

    def __fade_finished(self, window, fade_in):
        if fade_in:
            GLib.timeout_add(self.Conf.delay, self.start_fade_out, window)
        else:
            window.hide()
            if self.__current_window is window:
                self.__current_window = None
            # Delay destroy - apparently the hide does not quite register if
            # the destroy is done immediately.  The compiz animation plugin
            # then sometimes triggers and causes undesirable effects while the
            # popup should already be invisible.
            GLib.timeout_add(1000, window.destroy)
