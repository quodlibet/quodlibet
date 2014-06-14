# -*- coding: utf-8 -*-
# Copyright 2011, 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk

from quodlibet import qltk


class MenuButton(Gtk.ToggleButton):
    __menu = None
    __menu_sig = None

    def __init__(self, widget=None, arrow=False, down=True):
        super(MenuButton, self).__init__()

        bbox = Gtk.HBox(spacing=3)
        if widget:
            bbox.pack_start(widget, True, True, 0)
        if arrow:
            arrow_type = Gtk.ArrowType.DOWN if down else Gtk.ArrowType.UP
            bbox.pack_start(
                Gtk.Arrow.new(arrow_type, Gtk.ShadowType.IN),
                True, True, 0)

        self._down = down
        self.add(bbox)

        self.connect("toggled", self.__toggled_cb)
        self.connect("button-press-event", self.__press_cb)

        self.connect("destroy", self.__destroy)

    def get_menu(self):
        return self.__menu

    def set_menu(self, menu):
        if self.__menu:
            self.__menu.detach()
            self.__menu.disconnect(self.__menu_sig)

        self.__menu = menu
        menu.attach_to_widget(self, None)
        self.__menu_sig = menu.connect("deactivate",
                                       self.__menu_deactivate_cb, self)

    def __destroy(self, *args):
        if self.__menu:
            self.__menu.detach()
            self.__menu.disconnect(self.__menu_sig)
        self.__menu = None

    def __menu_deactivate_cb(self, menu, button):
        button.set_active(False)

    def __press_cb(self, widget, event):
        if self.__menu and event.button == Gdk.BUTTON_PRIMARY:
            widget.set_active(True)
            return True
        return False

    def _popup(self):
        event = Gtk.get_current_event()
        ok, button = event.get_button()
        if not ok:
            button = Gdk.BUTTON_PRIMARY
        time = event.get_time()

        if self._down:
            qltk.popup_menu_under_widget(self.__menu, self, button, time)
        else:
            qltk.popup_menu_above_widget(self.__menu, self, button, time)

    def __toggled_cb(self, widget):
        menu = self.__menu
        if widget.get_active() and menu:
            self._popup()
        elif menu:
            menu.popdown()
