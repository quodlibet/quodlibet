# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject
import gtk

import formats

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
        return bool(value and value.startswith(key))

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
    """A completion for text entries tied to a library's tag list."""

    __sig = None

    def __init__(self, library):
        super(LibraryTagCompletion, self).__init__()
        try: model = self.__model
        except AttributeError:
            model = type(self).__model = gtk.ListStore(str)
            library.connect('changed', self.__refreshmodel, model)
            library.connect('added', self.__refreshmodel, model)
            library.connect('removed', self.__refreshmodel, model)
            self.__refreshmodel(library, None, model)
        self.set_model(model)
        self.set_text_column(0)

    def __refreshmodel(klass, library, songs, model):
        if klass.__sig is not None:
            gobject.source_remove(klass.__sig)
        next = klass.__refreshmodel_real(library, model).next
        klass.__sig = gobject.idle_add(next)
    __refreshmodel = classmethod(__refreshmodel)

    def __refreshmodel_real(klass, library, model):
        tags = set()
        model.clear()
        yield True
        # If rescanning the entire library ends up being too slow,
        # optimize this by using 'songs' for added/changed, and
        # ignoring removed.
        for count, song in enumerate(library):
            for tag in song.keys():
                if not (tag.startswith("~#") or tag in formats.MACHINE_TAGS):
                    tags.add(tag)
            if count % 1000 == 0:
                yield True
        tags.update(["~dirname", "~basename", "~people", "~format"])
        for tag in ["track", "disc", "playcount", "skipcount", "lastplayed",
                    "mtime", "added", "rating", "length"]:
            tags.add("#(" + tag)
        for tag in ["date", "bpm"]:
            if tag in tags: tags.add("#(" + tag)
        yield True
        for tag in tags:
            model.append([tag])
        klass.__sig = None
        yield False
    __refreshmodel_real = classmethod(__refreshmodel_real)

class LibraryValueCompletion(gtk.EntryCompletion):
    """Entry completion for a library value, for a specific tag."""

    __sig = None

    def __init__(self, tag, library):
        super(LibraryValueCompletion, self).__init__()
        self.set_model(gtk.ListStore(str))
        self.set_text_column(0)
        self.set_tag(tag, library)

    def set_tag(self, tag, library):
        if tag is None:
            return
        elif tag in ("bpm date discnumber isrc originaldate recordingdate "
                     "tracknumber").split() + formats.MACHINE_TAGS:
            return
        elif tag in formats.PEOPLE:
            tag = "~people"

        if self.__sig is not None:
            gobject.source_remove(self.__sig)
        next = self.__fill_tag(tag, library).next
        self.__sig = gobject.idle_add(next)

    def __fill_tag(self, tag, library):
        model = self.get_model()
        model.clear()
        yield True
        values = sorted(library.tag_values(tag))
        self.set_minimum_key_length(int(len(values) > 100))
        yield True
        for count, value in enumerate(values):
            model.append(row=[value])
            if count % 1000 == 0:
                yield True
        self.__sig = None
        yield False
