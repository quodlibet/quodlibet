# Copyright 2005-2011 Joe Wreschnig, Michael Urman, Christoph Reiter
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
    except ImportError: pass

from quodlibet import config
from quodlibet.qltk.x import ClearButton, get_top_parent

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
            self.connect("delete-text", self.__delete_before)]

        self.__accels = gtk.AccelGroup()
        self.add_accelerator('undo', self.__accels, ord('z'),
            gtk.gdk.CONTROL_MASK, 0)
        self.add_accelerator('redo', self.__accels, ord('z'),
            gtk.gdk.SHIFT_MASK | gtk.gdk.CONTROL_MASK, 0)

        self.__rlz = self.connect('realize', self.__realize)

        self.__handlers.extend([
            self.connect('undo', lambda *x: self.undo()),
            self.connect('redo', lambda *x: self.redo()),
            self.connect('populate-popup', self.__popup)
            ])

    def __disable_undo(self):
        for handler in self.__handlers:
            self.disconnect(handler)

        del self.__history
        del self.__re_history
        del self.__last_space
        del self.__in_pos
        del self.__del_pos

    def __realize(self, *args):
        self.disconnect(self.__rlz)
        del self.__rlz
        parent = get_top_parent(self)
        parent.add_accel_group(self.__accels)

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
    """A clear icon mixin supporting newer gtk.Entry or sexy.IconEntry /
    a separate clear button as a fallback.
    """

    __gsignals__ = {'clear': (
        gobject.SIGNAL_RUN_LAST|gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ())}

    def pack_clear_button(self, container=None):
        """Enables the clear icon in the entry. For older gtk+
        versions and without libsexy, a clear button will be packed in
        container.
        """
        if getattr(self, "set_icon_from_stock", None):
            self.set_icon_from_stock(
                gtk.ENTRY_ICON_SECONDARY, gtk.STOCK_CLEAR)
            self.connect("icon-release", self.__clear)
        elif container:
            button = ClearButton(self)
            container.pack_start(button, False)
            button.connect('clicked', self.__clear)

    def __clear(self, button, *args):
        # TODO: don't change the order.. we connect to clear and remove all
        # timeouts added for text change in the searchbar
        self.delete_text(0, -1)
        self.emit('clear')

class ClearEntry(UndoEntry, ClearEntryMixin):
    __gsignals__ = ClearEntryMixin.__gsignals__
class ClearNoSexyEntry(UndoNoSexyEntry, ClearEntryMixin):
    __gsignals__ = ClearEntryMixin.__gsignals__

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
        super(ValidatingEntry, self).__init__(*args)
        self.set_validate(validator)

class ValidatingNoSexyEntry(ClearNoSexyEntry, ValidatingEntryMixin):
    def __init__(self, validator=None, *args):
        super(ValidatingNoSexyEntry, self).__init__(*args)
        self.set_validate(validator)
