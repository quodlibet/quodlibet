# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gi
try:
    gi.require_version("AppIndicator3", "0.1")
except ValueError as e:
    raise ImportError(e)

from gi.repository import AppIndicator3

from quodlibet import app
from quodlibet.util import is_plasma
from .base import BaseIndicator
from .util import pconfig
from .menu import IndicatorMenu


class AppIndicator(BaseIndicator):

    def __init__(self):
        # KDE doesn't support symbolic icons afaics
        icon_name = app.icon_name if is_plasma() else app.symbolic_icon_name
        self.indicator = AppIndicator3.Indicator.new(
            app.id, icon_name,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS)

        self.indicator.set_title(app.name)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.menu = IndicatorMenu(app, add_show_item=True)
        play_item = self.menu.get_play_item()
        self.indicator.set_secondary_activate_target(play_item)
        self.indicator.set_menu(self.menu)

        self.__w_sig_show = app.window.connect('show', self.__window_show)
        self.__w_sig_del = app.window.connect('delete-event',
                                              self.__window_delete)

    def set_paused(self, value):
        self.menu.set_paused(value)

    def set_song(self, song):
        self.menu.set_song(song)

    def remove(self):
        app.window.disconnect(self.__w_sig_show)
        app.window.disconnect(self.__w_sig_del)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
        self.indicator = None
        self.menu.destroy()
        self.menu = None

    def __window_delete(self, win, event):
        if pconfig.getboolean("window_hide"):
            self.__hide_window()
            return True
        return False

    def __window_show(self, win, *args):
        pconfig.set("window_visible", True)

    def __hide_window(self):
        app.hide()
        pconfig.set("window_visible", False)
