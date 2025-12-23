# Copyright 2006 Joe Wreschnig
#           2015 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet.util import tag
from quodlibet.util.tags import USER_TAGS


class _TagsCombo:
    __tags = sorted(USER_TAGS)

    def _fill_model(self, can_change):
        self.clear()
        render = Gtk.CellRendererText()
        self.prepend(render, True)
        self.add_attribute(render, "text", 1)

        if can_change is None:
            can_change = self.__tags
        can_change = sorted(can_change)

        model = self.get_model()
        for t in can_change:
            model.append(row=[t, f"{tag(t)} ({t})"])
        self.set_model(model)

        if len(model) == 0:
            raise ValueError("TagsCombo boxes require at least one tag name")

    @property
    def tag(self):
        return self._tag()


class TagsComboBox(Gtk.ComboBox, _TagsCombo):
    """A ComboBox containing a list of tags for the user to choose from.
    The tag names are presented both translated and untranslated.

    The 'tag' attribute is the currently chosen tag."""

    def __init__(self, can_change=None):
        super().__init__(model=Gtk.ListStore(str, str))
        self._fill_model(can_change)
        self.set_active(0)

    def _tag(self):
        iter = self.get_active_iter()
        return self.get_model()[iter][0]


class TagsComboBoxEntry(Gtk.ComboBox, _TagsCombo):
    """A ComboBoxEntry containing a list of tags for the user to choose from.
    The tag names are presented both translated and untranslated in the
    menu, but always untranslated when editing.

    The 'tag' attribute is the currently chosen tag."""

    def __init__(self, can_change=None, tooltip_markup=None):
        super().__init__(
            model=Gtk.ListStore(str, str), entry_text_column=0, has_entry=True
        )
        self._fill_model(can_change)
        if tooltip_markup:
            self.get_child().set_tooltip_markup(tooltip_markup)

    def _fill_model(self, can_change):
        super()._fill_model(can_change)
        comp = Gtk.EntryCompletion()
        comp.set_model(self.get_model())
        comp.set_text_column(0)
        self.get_child().set_completion(comp)

    def _tag(self):
        return self.get_child().get_text()
