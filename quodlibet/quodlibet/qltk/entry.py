# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#           2011, 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import math

from gi.repository import Gtk, GObject, Gdk, Gio, Pango

from quodlibet import _
from quodlibet.qltk import is_accel, add_fake_accel
from quodlibet.qltk.x import SeparatorMenuItem, MenuItem
from quodlibet.qltk import Icons
from quodlibet.util import gdecode
from quodlibet.compat import string_types


class EditableUndo(object):
    """A simple undo/redo implementation for gtk widgets that
    support the gtk.Editable interface"""

    def set_undo(self, val):
        if val:
            self.__enable_undo()
        else:
            self.__disable_undo()

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
        if is_accel(event, "<Primary>z"):
            self.undo()
            return True
        elif is_accel(event, "<Primary><shift>z"):
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
        undo = MenuItem(_("_Undo"), Icons.EDIT_UNDO)
        add_fake_accel(undo, "<Primary>z")
        redo = MenuItem(_("_Redo"), Icons.EDIT_REDO)
        add_fake_accel(redo, "<Primary><shift>z")
        sep = SeparatorMenuItem()

        for widget in [sep, redo, undo]:
            widget.show()

        undo.connect('activate', lambda *x: self.undo())
        redo.connect('activate', lambda *x: self.redo())

        undo.set_sensitive(self.can_undo())
        redo.set_sensitive(self.can_redo())

        for item in [sep, redo, undo]:
            menu.prepend(item)

    def __all(self):
        text = gdecode(self.get_chars(0, -1))
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
        if not self.__can_do(source):
            return
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


class Entry(Gtk.Entry):

    def __init__(self, *args, **kwargs):
        super(Entry, self).__init__(*args, **kwargs)
        self._max_width_chars = -1

        # the default is way too much
        self.set_width_chars(5)

    def set_max_width_chars(self, value):
        """Works with GTK+ <3.12"""

        self._max_width_chars = value
        self.queue_resize()

    def do_get_preferred_width(self):
        minimum, natural = Gtk.Entry.do_get_preferred_width(self)

        if self._max_width_chars >= 0:
            # based on gtkentry.c
            style_context = self.get_style_context()
            style_context.save()
            style_context.set_state(Gtk.StateFlags.NORMAL)
            border = style_context.get_border(style_context.get_state())
            padding = style_context.get_padding(style_context.get_state())
            style_context.restore()
            pango_context = self.get_pango_context()

            metrics = pango_context.get_metrics(
                pango_context.get_font_description(),
                pango_context.get_language())

            char_width = metrics.get_approximate_char_width()
            digit_width = metrics.get_approximate_digit_width()
            char_pixels = int(math.ceil(
                float(max(char_width, digit_width)) / Pango.SCALE))

            space = border.left + border.right + padding.left + padding.right
            nat_width = self._max_width_chars * char_pixels + space
            natural = max(nat_width, minimum)

        return (minimum, natural)


class UndoEntry(Entry, EditableUndo):
    def __init__(self, *args):
        super(UndoEntry, self).__init__(*args)
        self.set_undo(True)

    def set_text(self, *args):
        super(UndoEntry, self).set_text(*args)
        self.reset_undo()


class ClearEntryMixin(object):
    """A clear icon mixin supporting newer Gtk.Entry or
    a separate clear button as a fallback.
    """

    __gsignals__ = {
        'clear': (GObject.SignalFlags.RUN_LAST | GObject.SignalFlags.ACTION,
                  None, ())
    }

    def enable_clear_button(self):
        """Enables the clear icon in the entry"""

        gicon = Gio.ThemedIcon.new_from_names(
            ["edit-clear-symbolic", "edit-clear"])
        self.set_icon_from_gicon(Gtk.EntryIconPosition.SECONDARY, gicon)
        self.connect("icon-release", self.__clear)

    def clear(self):
        self.__do_clear()

    def __clear(self, button, *args):
        self.__do_clear()

    def __do_clear(self):
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
    """

    INVALID = Gdk.RGBA(0.8, 0, 0)
    VALID = Gdk.RGBA(0.3, 0.6, 0.023)

    def set_validate(self, validator=None):
        if validator:
            self.connect('changed', self.__color, validator)

    def __color(self, widget, validator):
        value = validator(gdecode(self.get_text()))
        if value is True:
            color = self.VALID
        elif value is False:
            color = self.INVALID
        elif value and isinstance(value, string_types):
            color = Gdk.RGBA()
            color.parse(value)
        else:
            color = None

        if color and self.get_property('sensitive'):
            self.override_color(Gtk.StateType.NORMAL, color)
        else:
            self.override_color(Gtk.StateType.NORMAL, None)


class ValidatingEntry(ClearEntry, ValidatingEntryMixin):
    def __init__(self, validator=None, *args):
        super(ValidatingEntry, self).__init__(*args)
        self.set_validate(validator)
