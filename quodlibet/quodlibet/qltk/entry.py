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

    def reset_undo(self):
        self.__history = []
        self.__re_history = []
        self.__in_pos = -1
        self.__del_pos = -1
        self.__last = ""

    def undo(self):
        self.__do(self.__history, self.__re_history)

    def redo(self):
        self.__do(self.__re_history, self.__history)

    def __enable_undo(self):
        self.reset_undo()

        self.__handlers = [
            self.connect("insert-text", self.__insert_before),
            self.connect("delete-text", self.__delete_before)]

        self.__accels = gtk.AccelGroup()
        self.add_accelerator('undo', self.__accels, ord('z'),
            gtk.gdk.CONTROL_MASK, 0)
        self.add_accelerator('redo', self.__accels, ord('z'),
            gtk.gdk.SHIFT_MASK | gtk.gdk.CONTROL_MASK, 0)

        self.__rlz = self.connect('realize', self.__realize)

        self.__handlers.extend([
            self.connect('undo', lambda *x: self.undo()),
            self.connect('redo', lambda *x: self.redo())
            ])

    def __disable_undo(self):
        for handler in self.__handlers:
            self.disconnect(handler)

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
        text = self.get_chars(0, -1).decode("utf-8")
        pos = self.get_position()
        return [text, pos]

    def __add(self):
        self.__history.append(self.__all())
        self.__re_history = []

    def __insert_before(self, entry, text, length, position):
        self.__del_pos = -1
        pos = self.get_position()
        if pos != self.__in_pos or (self.__last == " " and text != " ") \
            or length > 1:
            self.__add()
        self.__last = text
        self.__in_pos = pos + 1

    def __delete_before(self, entry, start, end):
        self.__in_pos = -1
        text = self.get_chars(start, end)
        length = end - start
        pos = self.get_position()
        if pos != self.__del_pos or (self.__last == " " and text != " ") \
            or length > 1:
            self.__add()
        self.__last = text
        self.__del_pos = end - 1

    def __inhibit(self):
        for handler in self.__handlers:
            self.handler_block(handler)

    def __uninhibit(self):
        for handler in self.__handlers:
            self.handler_unblock(handler)

    def __do(self, source, target):
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

    def set_text(self, *args, **kwargs):
        super(UndoEntry, self).set_text(*args, **kwargs)
        self.reset_undo()

class UndoNoSexyEntry(gtk.Entry, EditableUndo):
    __gsignals__ = EditableUndo.__gsignals__
    def __init__(self, *args):
        super(UndoNoSexyEntry, self).__init__(*args)
        self.set_undo(True)

    def set_text(self, *args):
        super(UndoNoSexyEntry, self).set_text(*args)
        self.reset_undo()

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
