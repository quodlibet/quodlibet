# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import gi
try:
    gi.require_version("AppIndicator3", "0.1")
except ValueError as e:
    raise ImportError(e)

from gi.repository import AppIndicator3, Gdk

import quodlibet
from quodlibet import _
from quodlibet import app
from quodlibet.util import is_plasma
from quodlibet.pattern import Pattern
from .base import BaseIndicator
from .util import pconfig
from .menu import IndicatorMenu


def get_next_app_id(state=[0]):
    """Returns an ever increasing app id variant.. I can't find a way
    to remove an indicator, so just hide old ones and add new different ones
    this way.
    """

    state[0] += 1
    return "%s-%d" % (app.id, state[0])


class AppIndicator(BaseIndicator):

    def __init__(self):
        # KDE doesn't support symbolic icons afaics
        icon_name = app.icon_name if is_plasma() else app.symbolic_icon_name
        self.indicator = AppIndicator3.Indicator.new(
            get_next_app_id(), icon_name,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS)

        self.indicator.set_icon_theme_path(quodlibet.get_image_dir())
        self.indicator.set_title(app.name)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.menu = IndicatorMenu(app, add_show_item=True)

        def on_action_item_changed(menu, indicator):
            indicator.set_secondary_activate_target(menu.get_action_item())

        self.menu.connect("action-item-changed",
                          on_action_item_changed,
                          self.indicator)
        action_item = self.menu.get_action_item()
        self.indicator.set_secondary_activate_target(action_item)
        self.indicator.set_menu(self.menu)
        self.__scroll_id = self.indicator.connect(
            "scroll_event", self.__on_scroll)

        self.__w_sig_del = app.window.connect('delete-event',
                                              self.__window_delete)

    def set_info_song(self, song):
        if song:
            try:
                pattern = Pattern(pconfig.get("tooltip"))
            except ValueError:
                tooltip = u""
            else:
                tooltip = pattern % song
        else:
            tooltip = _("Not playing")

        self.indicator.set_title(tooltip)

    def set_paused(self, value):
        self.menu.set_paused(value)

    def set_song(self, song):
        self.menu.set_song(song)

    def remove(self):
        # No function to remove an Indicator so it can be added back :(
        # If there is we can get rid of get_next_app_id()
        app.window.disconnect(self.__w_sig_del)
        self.indicator.disconnect(self.__scroll_id)
        self.__scroll_id = None
        self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
        self.indicator = None
        self.menu.destroy()
        self.menu = None

    def __on_scroll(self, indicator, steps, direction):
        # If direction here is always UP you're hitting
        # https://bugs.launchpad.net/indicator-application/+bug/1075152
        modifier_swap = pconfig.getboolean("modifier_swap")
        for step in range(steps):
            if direction == Gdk.ScrollDirection.UP:
                if modifier_swap:
                    app.player.previous()
                else:
                    app.player.volume += 0.05
            elif direction == Gdk.ScrollDirection.DOWN:
                if modifier_swap:
                    app.player.next()
                else:
                    app.player.volume -= 0.05

    def __window_delete(self, win, event):
        if pconfig.getboolean("window_hide"):
            self.__hide_window()
            return True
        return False

    def __hide_window(self):
        app.hide()
