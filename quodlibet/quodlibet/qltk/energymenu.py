# -*- coding: utf-8 -*-
# Copyright 2011-2013 Nick Boultbee
#           2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import util
from quodlibet import config
from quodlibet import qltk
from quodlibet.config import ENERGY
from quodlibet.qltk import SeparatorMenuItem
from quodlibet.util import connect_obj


class ConfirmEnergyMultipleDialog(qltk.Message):
    def __init__(self, parent, action_title, count, value):
        assert count > 1

        title = (_("Are you sure you want to change the "
                   "energy of all %d songs?") % count)
        desc = (_("The saved energy will be removed") if value is None
                else _("The energy of all selected songs will be changed to "
                       "'%s'") % util.format_energy(value))

        super(ConfirmEnergyMultipleDialog, self).__init__(
            Gtk.MessageType.WARNING, parent, title, desc, Gtk.ButtonsType.NONE)

        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(action_title, Gtk.ResponseType.YES)


class EnergyMenuItem(Gtk.MenuItem):
    __accels = Gtk.AccelGroup()

    def set_energy(self, value, songs, librarian):
        count = len(songs)
        if (count > 1 and
                config.getboolean("browsers", "energy_confirm_multiple")):
            parent = qltk.get_menu_item_top_parent(self)
            dialog = ConfirmEnergyMultipleDialog(
                parent, _("Change _Energy"), count, value)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        for song in songs:
            song["~#energy"] = value
        librarian.changed(songs)

    def remove_energy(self, songs, librarian):
        count = len(songs)
        if (count > 1 and
                config.getboolean("browsers", "energy_confirm_multiple")):
            parent = qltk.get_menu_item_top_parent(self)
            dialog = ConfirmEnergyMultipleDialog(
                parent, _("_Remove Energy"), count, None)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        reset = []
        for song in songs:
            if "~#energy" in song:
                del song["~#energy"]
                reset.append(song)
        librarian.changed(reset)

    def __init__(self, songs, library, label=_("_Energy")):
        super(EnergyMenuItem, self).__init__(label=label, use_underline=True)
        submenu = Gtk.Menu()
        self.set_submenu(submenu)
        for i in ENERGY.all:
            itm = Gtk.MenuItem(label="%0.2f\t%s" % (i, util.format_energy(i)))
            submenu.append(itm)
            connect_obj(itm, 'activate', self.set_energy, i, songs, library)
        reset = Gtk.MenuItem(label=_("_Remove energy"), use_underline=True)
        connect_obj(reset, 'activate', self.remove_energy, songs, library)
        submenu.append(SeparatorMenuItem())
        submenu.append(reset)
        submenu.show_all()
