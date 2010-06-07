# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gobject

# We use sexy.IconEntry with older GTK+, but ComboboxEntry only allows
# gtk.Entry (it kind of works, but alignment is wrong and there are lots of
# warnings), so also provide all entries without libsexy.

IconEntry = gtk.Entry
if not getattr(gtk.Entry, "set_icon_from_stock", None):
    try: from sexy import IconEntry
    except: pass

from quodlibet import config
from quodlibet.qltk import ClearButton, get_top_parent

class EditableUndo(object):
    """A simple undo/redo implementation for gtk widgets that
    support the gtk.Editable interface"""

    __gsignals__ = {
        "undo": (
        gobject.SIGNAL_RUN_LAST|gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ()),
        "redo": (
        gobject.SIGNAL_RUN_LAST|gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ())}

    def set_undo(self, val):
        if val: self.__enable_undo()
        else: self.__disable_undo()

    def __enable_undo(self):
        self.__buffer = ""
        self.__history = [self.__all()]
        self.__re_history = []
        self.__last = ""
        self.__in_pos = 0
        self.__del_pos = 0

        self.__handlers = [
            self.connect_after("insert-text", self.__insert_after),
            self.connect("insert-text", self.__insert_before),
            self.connect("delete-text", self.__delete_before),
            self.connect_after("delete-text", self.__delete_after)]

        self.__accels = gtk.AccelGroup()
        self.add_accelerator('undo', self.__accels, ord('z'),
            gtk.gdk.CONTROL_MASK, 0)
        self.add_accelerator('redo', self.__accels, ord('z'),
            gtk.gdk.SHIFT_MASK | gtk.gdk.CONTROL_MASK, 0)

        self.__rlz = self.connect('realize', self.__realize)

        self.__handlers.extend([
            self.connect('undo', self.__do, self.__history, self.__re_history),
            self.connect('redo', self.__do, self.__re_history, self.__history)
            ])

    def __disable_undo(self):
        for handler in self.__handlers:
            self.disconnect(handler)

        del self.__buffer
        del self.__history
        del self.__re_history
        del self.__last
        del self.__in_pos
        del self.__del_pos

    def __realize(self, *args):
        self.disconnect(self.__rlz)
        del self.__rlz
        parent = get_top_parent(self)
        parent.add_accel_group(self.__accels)

    def __all(self):
        return [self.get_chars(0, -1), self.get_position()]

    def __add(self):
        all, pos = self.__all()
        if self.__history and self.__history[-1][0] == all:
            self.__history[-1][1] = pos
        else:
            self.__history.append([all, pos])
        self.__re_history = []

    def __insert_after(self, entry, text, length, position):
        if (length > 1 and self.get_position() > 0) or text == "\n":
            self.__add()
        self.__last = text

    def __insert_before(self, entry, text, length, position):
        self.__del_pos = 0
        pos = self.get_position()
        if pos != self.__in_pos or (self.__last == " " and text != " ") \
            or text == "\n":
            self.__add()
        self.__in_pos = pos +  length

    def __delete_after(self, entry, start, end):
        text = self.get_chars(start, end)
        all = self.get_chars(0, -1)
        if not all or (self.__last == " " and text != " ") or text == "\n":
            self.__add()
        self.__last = text

    def __delete_before(self, entry, start, end):
        self.__in_pos = 0
        pos = self.get_position()
        if pos != self.__del_pos:
            self.__add()
        self.__del_pos = pos - (end - start)

    def __inhibit(self):
        for handler in self.__handlers:
            self.handler_block(handler)

    def __uninhibit(self):
        for handler in self.__handlers:
            self.handler_unblock(handler)

    def __do(self, entry, source, target):
        if not source: return
        self.__del_pos = self.__in_pos = -1
        self.__inhibit()
        now = self.__all()
        last = source.pop(-1)
        if now != last:
            target.append(now)
        text, pos = last
        self.delete_text(0, -1)
        self.insert_text(text, 0)
        self.set_position(pos)
        self.__uninhibit()

class UndoEntry(IconEntry, EditableUndo):
    __gsignals__ = EditableUndo.__gsignals__
    def __init__(self, *args, **kwargs):
        super(UndoEntry, self).__init__(*args, **kwargs)
        self.set_undo(True)

class UndoNoSexyEntry(gtk.Entry, EditableUndo):
    __gsignals__ = EditableUndo.__gsignals__
    def __init__(self, *args, **kwargs):
        super(UndoNoSexyEntry, self).__init__(*args, **kwargs)
        self.set_undo(True)

class ClearEntryMixin(object):
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

class ClearEntry(UndoEntry, ClearEntryMixin): pass
class ClearNoSexyEntry(UndoNoSexyEntry, ClearEntryMixin): pass

class ValidatingEntryMixin(object):
    """An entry with visual feedback as to whether it is valid or not.
    The given validator function gets a string and returns True (green),
    False (red), or a color string, or None (black).

    parse.Query.is_valid_color mimicks the behavior of the search bar.

    If the "Color search terms" option is off, the entry will not
    change color."""

    def set_validate(self, validator=None):
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

class ValidatingEntry(ClearEntry, ValidatingEntryMixin):
   def __init__(self, validator=None, *args):
       super(ValidatingEntry,self).__init__(*args)
       self.set_validate(validator)

class ValidatingNoSexyEntry(ClearNoSexyEntry, ValidatingEntryMixin):
   def __init__(self, validator=None, *args):
       super(ValidatingNoSexyEntry,self).__init__(*args)
       self.set_validate(validator)
