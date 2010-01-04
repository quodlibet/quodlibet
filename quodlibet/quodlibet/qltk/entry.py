# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

IconEntry = gtk.Entry
if not getattr(gtk.Entry, "set_icon_from_stock", None):
    try: from sexy import IconEntry
    except: pass

from quodlibet import config
from quodlibet.qltk import ClearButton

class ClearEntry(IconEntry):
    def pack_clear_button(self, container=None):
        if getattr(self, "set_icon_from_stock", None):
            self.set_icon_from_stock(
                gtk.ENTRY_ICON_SECONDARY, gtk.STOCK_CLEAR)
            clear = lambda *x: x[0].set_text("")
            self.connect("icon-release", clear)
        elif getattr(self, "add_clear_button", None):
            self.add_clear_button()
        else:
            container.pack_start(ClearButton(self), False)

class ValidatingEntry(ClearEntry):
    """An entry with visual feedback as to whether it is valid or not.
    The given validator function gets a string and returns True (green),
    False (red), or a color string, or None (black).

    parse.Query.is_valid_color mimicks the behavior of the search bar.

    If the "Color search terms" option is off, the entry will not
    change color."""

    def __init__(self, validator=None, *args):
        super(ValidatingEntry, self).__init__(*args)
        if validator: self.connect_object('changed', self.__color, validator)

    def __color(self, validator):
        if config.getboolean('browsers', 'color'):
            value = validator(self.get_text())
            if value is True: color = "dark green"
            elif value is False: color = "red"
            elif isinstance(value, str): color = value
            else: color = None

            if color and self.get_property('sensitive'):
                self.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(color))
        else:
            self.modify_text(gtk.STATE_NORMAL, None)
