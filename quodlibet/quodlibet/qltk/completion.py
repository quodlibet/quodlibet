# Copyright 2005 Joe Wreschnig, Michael Urman,
#           2011 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
from quodlibet import formats, config, print_d
from quodlibet.util import copool, massagers



class EntryWordCompletion(gtk.EntryCompletion):
    """Entry completion for simple words, where a word boundary is
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

    __tags = set()

    def __init__(self, library):
        super(LibraryTagCompletion, self).__init__()
        try: model = self.__model
        except AttributeError:
            model = type(self).__model = gtk.ListStore(str)
            library.connect('changed', self.__update_song, model)
            library.connect('added', self.__update_song, model)
            library.connect('removed', self.__update_song, model)
            copool.add(self.__build_model, library, model)
        self.set_model(model)
        self.set_text_column(0)

    @classmethod
    def __update_song(klass, library, songs, model):
        print_d("Updating tag model for %d songs" % len(songs))
        tags = klass.__tags
        for song in songs:
            for tag in song.keys():
                if not (tag.startswith("~#") or tag in formats.MACHINE_TAGS
                        or tag in tags):
                    klass.__tags.add(tag)
                    model.append([tag])
        print_d("Done updating tag model for %d songs" % len(songs))

    @classmethod
    def __build_model(klass, library, model):
        print_d("Updating tag model for whole library")
        all_tags = klass.__tags
        model.clear()

        tags = set()
        songs = list(library)
        for count, song in enumerate(songs):
            for tag in song.keys():
                if not (tag.startswith("~#") or tag in formats.MACHINE_TAGS):
                    tags.add(tag)

            if count % 500 == 0 or count + 1 == len(songs):
                tags -= all_tags
                for tag in tags:
                    model.append([tag])
                all_tags.update(tags)
                tags.clear()
                yield True

        tags.update(["~dirname", "~basename", "~people", "~format"])
        for tag in ["track", "disc", "playcount", "skipcount", "lastplayed",
                    "mtime", "added", "rating", "length"]:
            tags.add("#(" + tag)
        for tag in ["date", "bpm"]:
            if tag in all_tags: tags.add("#(" + tag)

        tags -= all_tags
        for tag in tags:
            model.append([tag])
        all_tags.update(tags)

        print_d("Done updating tag model for whole library")

class LibraryValueCompletion(gtk.EntryCompletion):
    """Entry completion for a library value, for a specific tag.
    Will add valid values from the tag massager where available"""

    def __init__(self, tag, library):
        super(LibraryValueCompletion, self).__init__()
        self.set_model(gtk.ListStore(str))
        self.set_text_column(0)
        self.set_tag(tag, library)

    def set_tag(self, tag, library):
        if not config.getboolean("settings", "eager_search"):
            return
        elif tag is None:
            return
        elif tag in ("bpm date discnumber isrc originaldate recordingdate "
                     "tracknumber title").split() + formats.MACHINE_TAGS:
            return
        elif tag in formats.PEOPLE:
            tag = "~people"
        copool.add(self.__fill_tag, tag, library)

    def __fill_tag(self, tag, library):
        model = self.get_model()
        model.clear()
        yield True
        # Issue 439: pre-fill with valid values if available
        if tag in massagers.tags:
            values = massagers.tags[tag].options
        else: values = []
        values = sorted(set(values + library.tag_values(tag)))
        self.set_minimum_key_length(int(len(values) > 100))
        yield True
        for count, value in enumerate(values):
            model.append(row=[value])
            if count % 1000 == 0:
                yield True
