# -*- coding: utf-8 -*-
# Copyright 2017 Pete Beardmore
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.qltk.pluginwin import PluginWindow
from quodlibet.plugins import PluginManager

from quodlibet import config
from quodlibet import _

from quodlibet.qltk import get_top_parent
from quodlibet.qltk import Icons
from quodlibet.qltk.menubutton import SmallMenuButton
from quodlibet.qltk.x import ScrolledWindow, SymbolicIconImage, \
    SmallImageButton, MenuItem, PaneLock

from gi.repository import Gtk


class WidgetBar(Gtk.Expander):

    def __init__(self, id):
        super(WidgetBar, self).__init__(spacing=1)

        self.id = id
        self.panelock = PaneLock(self.id, Gtk.Orientation.VERTICAL, 100)
        self.panelock.size = config.getint("plugins",
                                 self.id + "_size", self.default_size)

        self.title = Gtk.Label()
        self.title.set_alignment(0.0, 0.5)
        self.set_label_widget(self.title)
        title_height = self.get_label_widget().get_allocation().height

        expanded = config.getboolean("plugins", self.id + "_expanded", True)

        self.set_size_request(-1, self.panelock.size if expanded
                                                     else title_height + 5)

        self.scroll = ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.scroll.set_shadow_type(Gtk.ShadowType.NONE)

        self.preferences_cb = self.__preferences

        outer = Gtk.HBox()
        self.box_left = Gtk.HBox()
        self.box_right = Gtk.HBox()
        self.box = Gtk.HBox()
        controls_box = Gtk.VBox()

        outer.pack_start(self.box_left, False, False, 0)
        self.scroll.add(self.box)
        outer.pack_start(self.scroll, True, True, 0)
        outer.pack_start(self.box_right, False, False, 0)
        outer.pack_end(controls_box, False, False, 0)

        self.menu = Gtk.Menu()
        menuitem_prefs = MenuItem(_("_Preferences"), Icons.EDIT_CLEAR)
        self.menu.append(menuitem_prefs)
        menuitem_prefs.connect("activate", self.preferences)

        button_menu = SmallMenuButton(
            SymbolicIconImage(Icons.EMBLEM_SYSTEM, Gtk.IconSize.MENU),
            arrow=True)
        button_menu.set_relief(Gtk.ReliefStyle.NONE)
        button_menu.show_all()
        button_menu.set_no_show_all(True)
        self.menu.show_all()
        button_menu.set_menu(self.menu)

        aligntop = Gtk.Alignment()
        aligntop.set(1.0, 0.5, 0, 0)
        aligntop.add(button_menu)
        controls_box.pack_start(aligntop, False, True, 0)

        button_close = SmallImageButton(
            image=SymbolicIconImage("window-close", Gtk.IconSize.MENU),
            relief=Gtk.ReliefStyle.NONE)
        button_close.connect("clicked", lambda *x: self.__disable())
        controls_box.pack_end(button_close, False, True, 0)

        self.title.set_text(self.id)
        self.add(outer)

        self.connect('notify::expanded', self.__expand, button_menu)
        self.connect('size_allocate', self.__size_allocate)
        self.connect("destroy", self.__destroy)

        self.set_expanded(expanded)

    @property
    def default_size(self):
        return self.panelock.default_size

    @default_size.setter
    def default_size(self, value):
        self.panelock.default_size = value

    def preferences(self, data):
        if self.preferences_cb:
            self.preferences_cb()

    def __preferences(self):
        plugins_window = PluginWindow(get_top_parent(self))
        plugins_window.show()
        plugins_window.move_to(self.id)

    def __expand(self, widget, prop, menu_button):
        expanded = self.get_expanded()
        config.set("plugins", self.id + "_expanded", str(expanded))

        if self.get_parent():
            self.panelock.updating = True
            self.get_parent().update(self)
            self.get_parent().check_resize()
            self.panelock.updating = False

    def __disable(self):
        pm = PluginManager.instance
        plugin = next((p for p in pm.plugins if p.id == self.id), None)
        if plugin:
            pm.enable(plugin, False)
            pm.save()
        self.__save()

    def __destroy(self, *args):
        # no guarantee that this will be called -> :(
        self.__save()

    def __save(self):
        config.set("plugins", self.id + "_size", self.panelock.size)

    def __size_allocate(self, widget, allocation):

        if not self.get_expanded():
            title_height = self.get_label_widget().get_allocation().height
            self.set_size_request(-1, title_height + 5)
        self.get_parent().queue_resize()
        self.get_parent().check_resize()

        self.panelock.size_allocate(allocation)
        # persistence overkill as __destroy failing
        config.set("plugins", self.id + "_size", self.panelock.size)
