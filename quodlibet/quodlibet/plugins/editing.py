# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

class RenameFilesPlugin(object):
    """Plugins of this type must subclass a GTK widget. They will be
    packed into the RenameFiles pane (currently a ScrolledWindow hidden
    with an expander, but that might change).

    The 'filter' function will be called with the song's original filename
    as a string (probably in the local filesystem encoding) and the proposed
    new filename as a unicode object. It should return an
    appropriate-transformed filename, still as a unicode object.

    The plugin must provide either a 'changed' or 'preview'. 'preview'
    causes the entire display to be re-previewed. 'changed' causes the
    Preview button to made sensitive, and Save to be disabled.

    If the 'active' attribute is false, the filter will not be called.
    This is particularly useful for gtk.CheckButtons.

    The '_order' attribute decides the sort order of the plugin. The
    default filters have orders between 1 and 2. Plugins have order 0 by
    default. Plugins with equal orders are sorted by class name."""

    _order = 0.0
    active = False

    def filter(self, original_filename, value): return value
    def filter_list(self, origs, names): return map(self.filter, origs, names)

    def __cmp__(self, other):
        return (cmp(self._order, other._order) or
                cmp(type(self).__name__, type(other).__name__))

class TagsFromPathPlugin(object):
    """Plugins of this type must subclass a GTK widget. They will be
    packed into the TagsFromPath pane (currently a ScrolledWindow hidden
    with an expander, but that might change).

    The 'filter' function will be called with the tag and proposed value
    as a unicode object. It should return an appropriate-transformed
    filename, still as a unicode object.

    If you need to work on a set of filenames at once, you should
    instead overload the 'filter_list' function, which takes two lists;
    one of original filenames, the other of proposed new filenames.
    The default filter_list function calls filter on each item.

    The plugin must provide either a 'changed' or 'preview'. 'preview'
    causes the entire display to be re-previewed. 'changed' causes the
    Preview button to made sensitive, and Save to be disabled.

    If the 'active' attribute is false, the filter will not be called.
    This is particularly useful for gtk.CheckButtons.

    The '_order' attribute decides the sort order of the plugin. The
    default filters have orders between 1 and 2. Plugins have order 0 by
    default. Plugins with equal orders are sorted by class name."""

    _order = 0
    active = False

    def filter(self, tag, value): return value

    def __cmp__(self, other):
        return (cmp(self._order, other._order) or
                cmp(type(self).__name__, type(other).__name__))

class EditTagsPlugin(gtk.ImageMenuItem):
    """Plugins of this type are subclasses of gtk.ImageMenuItem.
    They will be added to the context menu of the EditTags tree view.

    The 'tags' attribute is a list of tags this plugin should appear on,
    or false if it should appear for all tags. This must be a class
    attribute, as it is checked before instantiation.

    The 'needs' attribute is a list of tags that must be editable in
    the currently selected songs for the plugin to be sensitive.

    The constructor is called with the tag and value for that row. This
    can be used to set the sensitivity of the menu item, or change its
    text.

    When clicked, the 'activated' function is called on the object,
    again with the tag name and value. It should return a list of
    (tag, value) tuples to replace the previous tag/value with.

    The '_order' attribute decides the sort order of the plugin. The
    default items have orders between 0 and 1. Plugins have order 2.0 by
    default. Plugins with equal orders are sorted by class name.

    How to Handle Submenus
    ----------------------
    If the menu item is given a submenu, magic happens. In particular,
    the callbacks are proxied to the submenu's items, and are attached,
    via connect_object, to make sure activated is called on the original
    item.

    So, to handle submenus,
      1. Make a submenu and attach it to your menu item.2
      2. To each item in the submenu, attach its 'activate' signal to
         something appropriate to prepare the original item's
         activated method,
      3. Because that method will be called after the subitem is
         clicked on, and your activate handler runs.
    """

    tags = []
    needs = []
    _order = 2.0

    def activated(self, tag, value): return [(tag, value)]

    def connect(self, signal, callback, *args, **kwargs):
        if self.get_submenu():
            for item in self.get_submenu().get_children():
                item.connect_object(signal, callback, self, *args, **kwargs)
        else:
            super(EditTagsPlugin, self).connect(
                signal, callback, *args, **kwargs)
