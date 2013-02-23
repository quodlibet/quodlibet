# -*- coding: utf-8 -*-
# Copyright 2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import qltk


class MenuButton(Gtk.ToggleButton):
    __menu = None
    __menu_sig = None

    def __init__(self, widget, arrow=False):
        super(MenuButton, self).__init__()

        bbox = Gtk.HBox(spacing=3)
        bbox.pack_start(widget, True, True, 0)
        if arrow:
            bbox.pack_start(Gtk.Arrow(Gtk.ArrowType.DOWN, Gtk.ShadowType.IN),
                            True, True, 0)

        self.add(bbox)

        self.connect("toggled", self.__toggled_cb)
        self.connect("button-press-event", self.__press_cb)

        self.connect("destroy", self.__destroy)

    def get_menu(self):
        return self.__menu

    def set_menu(self, menu):
        if self.__menu:
            self.__menu.disconnect(self.__menu_sig)

        self.__menu = menu
        self.__menu_sig = menu.connect("deactivate",
                                       self.__menu_deactivate_cb, self)

    def __destroy(self, *args):
        if self.__menu:
            self.__menu.disconnect(self.__menu_sig)
        self.__menu = None

    def __menu_deactivate_cb(self, menu, button):
        button.set_active(False)

    def __press_cb(self, widget, event):
        if self.__menu and event.button == 1:
            qltk.popup_menu_under_widget(
                self.__menu, widget, event.button, event.time)
            widget.set_active(True)
        return False

    def __toggled_cb(self, widget):
        menu = self.__menu
        if widget.get_active() and menu:
            time = Gtk.get_current_event_time()
            qltk.popup_menu_under_widget(menu, widget, 0, time)
        elif menu:
            menu.popdown()
