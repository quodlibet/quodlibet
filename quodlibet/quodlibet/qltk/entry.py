# Copyright 2005 Joe Wreschnig, Michael Urman
#           2011, 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gobject

IconEntry = gtk.Entry

from quodlibet.qltk.x import is_accel


class EditableUndo(object):
    """A simple undo/redo implementation for gtk widgets that
    support the gtk.Editable interface"""

    def set_undo(self, val):
        if val: self.__enable_undo()
        else: self.__disable_undo()

    def reset_undo(self):
        self.__history = []
        self.__re_history = []
        self.__in_pos = -1
        self.__del_pos = -1
        self.__last_space = False

    def undo(self):
        self.__do(self.__history, self.__re_history)

    def redo(self):
        self.__do(self.__re_history, self.__history)

    def can_undo(self):
        return self.__can_do(self.__history)

    def can_redo(self):
        return self.__can_do(self.__re_history)

    def __enable_undo(self):
        self.reset_undo()

        self.__handlers = [
            self.connect("insert-text", self.__insert_before),
            self.connect("delete-text", self.__delete_before),
            self.connect('populate-popup', self.__popup),
            self.connect('key-press-event', self.__key_press),
            ]

    def __key_press(self, entry, event):
        if is_accel(event, "<ctrl>z"):
            self.undo()
            return True
        elif is_accel(event, "<ctrl><shift>z"):
            self.redo()
            return True
        return False

    def __disable_undo(self):
        for handler in self.__handlers:
            self.disconnect(handler)

        del self.__history
        del self.__re_history
        del self.__last_space
        del self.__in_pos
        del self.__del_pos

    def __popup(self, entry, menu):
        undo =  gtk.ImageMenuItem(gtk.STOCK_UNDO)
        redo =  gtk.ImageMenuItem(gtk.STOCK_REDO)
        sep = gtk.SeparatorMenuItem()

        map(gtk.Widget.show, (sep, redo, undo))

        undo.connect('activate', lambda *x: self.undo())
        redo.connect('activate', lambda *x: self.redo())

        undo.set_sensitive(self.can_undo())
        redo.set_sensitive(self.can_redo())

        map(menu.prepend, (sep, redo, undo))

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
        if pos != self.__in_pos or (self.__last_space and text != " ") \
            or length > 1:
            self.__add()
        self.__last_space = (text == " ")
        self.__in_pos = pos + 1

    def __delete_before(self, entry, start, end):
        self.__in_pos = -1
        text = self.get_chars(start, end)
        length = end - start
        pos = self.get_position()
        if pos != self.__del_pos or (self.__last_space and text != " ") \
            or length > 1:
            self.__add()
        self.__last_space = (text == " ")
        self.__del_pos = end - 1

    def __inhibit(self):
        for handler in self.__handlers:
            self.handler_block(handler)

    def __uninhibit(self):
        for handler in self.__handlers:
            self.handler_unblock(handler)

    def __can_do(self, source):
        return bool(source)

    def __do(self, source, target):
        if not self.__can_do(source): return
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


class UndoEntry(gtk.Entry, EditableUndo):
    def __init__(self, *args):
        super(UndoEntry, self).__init__(*args)
        self.set_undo(True)

    def set_text(self, *args):
        super(UndoEntry, self).set_text(*args)
        self.reset_undo()


class ClearEntryMixin(object):
    """A clear icon mixin supporting newer gtk.Entry or sexy.IconEntry /
    a separate clear button as a fallback.
    """

    __gsignals__ = {'clear': (
        gobject.SIGNAL_RUN_LAST|gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ())}

    def enable_clear_button(self):
        """Enables the clear icon in the entry"""

        self.set_icon_from_stock(
            gtk.ENTRY_ICON_SECONDARY, gtk.STOCK_CLEAR)
        self.connect("icon-release", self.__clear)

    def __clear(self, button, *args):
        # TODO: don't change the order.. we connect to clear and remove all
        # timeouts added for text change in the searchbar
        self.delete_text(0, -1)
        self.emit('clear')


class ClearEntry(UndoEntry, ClearEntryMixin):
    __gsignals__ = ClearEntryMixin.__gsignals__


class ValidatingEntryMixin(object):
    """An entry with visual feedback as to whether it is valid or not.
    The given validator function gets a string and returns True (green),
    False (red), or None (black).

    parse.Query.is_valid_color mimicks the behavior of the search bar.

    If the "Color search terms" option is off, the entry will not
    change color."""

    INVALID = gtk.gdk.Color(*[c * 255 for c in (0xcc, 0x0, 0x0)])
    VALID = gtk.gdk.Color(*[c * 180 for c in (0x4e, 0x9a, 0x06)])

    def set_validate(self, validator=None):
        if validator: self.connect_object('changed', self.__color, validator)

    def __color(self, validator):
        value = validator(self.get_text())
        if value is True: color = self.VALID
        elif value is False: color = self.INVALID
        elif value and isinstance(value, str):
            color = gtk.gdk.color_parse(value)
        else: color = None

        if color and self.get_property('sensitive'):
            self.modify_text(gtk.STATE_NORMAL, color)
        else:
            self.modify_text(gtk.STATE_NORMAL, None)


class ValidatingEntry(ClearEntry, ValidatingEntryMixin):
    def __init__(self, validator=None, *args):
        super(ValidatingEntry, self).__init__(*args)
        self.set_validate(validator)
