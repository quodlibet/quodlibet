# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet.util import tag

import quodlibet.formats

class _TagsCombo(object):
    __tags = sorted(quodlibet.formats.USEFUL_TAGS)

    def _fill_model(self, can_change):
        self.clear()
        render = gtk.CellRendererText()
        self.pack_start(render, True)
        self.add_attribute(render, 'text', 1)

        if can_change is None:
            can_change = self.__tags
        can_change = sorted(can_change)

        model = self.get_model()
        for t in can_change:
            model.append(row=[t, "%s (%s)" % (tag(t), t)])
        self.set_model(model)

        if len(model) == 0:
            raise ValueError("TagsCombo boxes require at least one tag name")

    def __tag(self): return self._tag()
    tag = property(__tag)

class TagsComboBox(_TagsCombo, gtk.ComboBox):
    """A ComboBox containing a list of tags for the user to choose from.
    The tag names are presented both translated and untranslated.

    The 'tag' attribute is the currently chosen tag."""

    def __init__(self, can_change=None):
        super(TagsComboBox, self).__init__(gtk.ListStore(str, str))
        self._fill_model(can_change)
        self.set_active(0)

    def _tag(self):
        iter = self.get_active_iter()
        return self.get_model()[iter][0]

class TagsComboBoxEntry(_TagsCombo, gtk.ComboBoxEntry):
    """A ComboBoxEntry containing a list of tags for the user to choose from.
    The tag names are presented both translated and untranslated in the
    menu, but always untranslated when editing.

    The 'tag' attribute is the currently chosen tag."""

    def __init__(self, can_change=None):
        super(TagsComboBoxEntry, self).__init__(gtk.ListStore(str, str), 0)
        self._fill_model(can_change)

    def _fill_model(self, can_change):
        super(TagsComboBoxEntry, self)._fill_model(can_change)
        comp = gtk.EntryCompletion()
        comp.set_model(self.get_model())
        comp.set_text_column(0)
        self.child.set_completion(comp)

    def _tag(self):
        return self.child.get_text()
