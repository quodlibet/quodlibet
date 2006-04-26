# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import sys

import gtk

from const import MACHINE_TAGS

if sys.version_info < (2, 4):
    from sets import Set as set

class EntryWordCompletion(gtk.EntryCompletion):
    """Entry completion for simple words, where a word boundry is
    roughly equivalent to the separators in the QL query language.

    You need to manually set a model containing the available words."""

    leftsep = ["&(", "|(", ",", ", "]
    rightsep = [" ", ")", ","]

    def __init__(self):
        super(EntryWordCompletion, self).__init__()
        self.set_match_func(self.__match_filter)
        self.connect('match-selected', self.__match_selected)

    def __match_filter(self, completion, entrytext, iter):
        model = completion.get_model()
        entry = self.get_entry()
        entrytext = entrytext.decode('utf-8')
        if entry is None: return False
        cursor = entry.get_position()
        if (cursor != len(entrytext) and not
            max([entrytext[cursor:].startswith(s) for s in self.rightsep])):
            return False

        # find the border to the left
        left, f = max(
            [(entrytext.rfind(c, 0, cursor), c) for c in self.leftsep])
        if left < 0: left += 1
        else: left += len(f)

        if left == cursor: return False
        key = entrytext[left:cursor]

        value = model.get_value(iter, self.get_property('text-column'))
        if value is None: return False
        return value.startswith(key)

    def __match_selected(self, completion, model, iter):
        value = model.get_value(iter, self.get_property('text-column'))
        entry = self.get_entry()
        cursor = entry.get_position()

        text = entry.get_text()
        text = text.decode('utf-8')
        left, f = max(
            [(text.rfind(c, 0, cursor), c) for c in self.leftsep])
        if left == -1: left += 1
        else: left += len(f)
        offset = cursor - left

        entry.insert_text(value[offset:], cursor)
        entry.set_position(left + len(value))
        return True

class LibraryTagCompletion(EntryWordCompletion):
    """A completion for text entries that is tied to a library and watcher.

    FIXME: This needs to be abstracted to actually support multiple
    libraries and watchers; right now all instances are tied to the first
    library passed in (which is the main QL library)."""

    def __init__(self, watcher, lib):
        super(LibraryTagCompletion, self).__init__()
        try: model = self.__model
        except AttributeError:
            model = type(self).__model = gtk.ListStore(str)
            watcher.connect('changed', self.__refreshmodel, lib)
            watcher.connect('added', self.__refreshmodel, lib)
            watcher.connect('removed', self.__refreshmodel, lib)
            self.__refreshmodel(None, None, lib)
        self.set_model(model)
        self.set_text_column(0)

    def __refreshmodel(self, watcher, songs, library):
        tags = set()
        for song in library.itervalues():
            for tag in song.keys():
                if not (tag.startswith("~#") or tag in MACHINE_TAGS):
                    tags.add(tag)
        tags.update(["~dirname", "~basename", "~people", "~format"])
        for tag in ["track", "disc", "playcount", "skipcount", "lastplayed",
                    "mtime", "added", "rating", "length"]:
            tags.add("#(" + tag)
        for tag in ["date", "bpm"]:
            if tag in tags: tags.add("#(" + tag)
        self.__model.clear()
        for tag in tags:
            self.__model.append([tag])
