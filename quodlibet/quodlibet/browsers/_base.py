# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import random

from gi.repository import Gtk, GObject, GLib, Pango

from quodlibet import app, qltk
from quodlibet import util
from quodlibet import _
from quodlibet.pattern import XMLFromMarkupPattern
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.textedit import PatternEditBox
from quodlibet.util import connect_obj, print_d
from quodlibet.util.i18n import numeric_phrase
from quodlibet.util.library import background_filter


class Filter(object):

    active_filter = None
    """A callable that returns True if the passed song should be in the
    song list, False if not and None if no filter is active.
    Used for adding new songs to the song list or
    dynamic playlist removal when a song ends.
        def active_filter(self, song): ...
    """

    def can_filter_tag(self, key):
        """If key can be passed to filter()"""
        return False

    def can_filter_text(self):
        """If filter_text() and get_filter_text() can be used"""
        return False

    def filter_text(self, text):
        """Set a text query"""
        raise NotImplementedError

    def get_filter_text(self):
        """Get the active text query"""

        raise NotImplementedError

    def can_filter_albums(self):
        """If filter_albums() can be used"""
        return False

    def filter_albums(self, values):
        """Do filtering base on a list of album keys"""
        raise NotImplementedError

    def list_albums(self):
        """Return a list of unique album keys (song.album_key)"""
        albums = app.library.albums
        albums.load()
        return [a.key for a in albums]

    def filter(self, key, values):
        """Actually do the filtering (with a union of values)."""
        # for backward compatibility
        if self.can_filter_text():
            self.filter_text(util.build_filter_query(key, values))

    def list(self, tag):
        """Return a list of unique values for the given tag. This needs to be
        here since not all browsers pull from the default library.
        """
        library = app.library
        bg = background_filter()
        if bg:
            songs = filter(bg, library.values())
            return list({value
                         for song in songs
                         for value in song.list(tag)})
        return list(library.tag_values(tag))

    def unfilter(self):
        """Reset all filters and display the whole library."""
        pass

    def can_filter(self, key):
        """If key can be passed to filter_on() or filter_random()"""
        c = self.can_filter_text()
        c = c or (key == "album" and self.can_filter_albums())
        return c or (key is not None and self.can_filter_tag(key))

    def filter_on(self, songs, key):
        """Do filtering in the best way the browser can handle"""
        if key == "album" and self.can_filter_albums():
            values = {s.album_key for s in songs}
            self.filter_albums(values)
        elif self.can_filter_tag(key) or self.can_filter_text():
            values = set()
            if key.startswith("~#"):
                values.update([song(key, 0) for song in songs])
            else:
                for song in songs:
                    values.update(song.list(key))

            if self.can_filter_tag(key):
                self.filter(key, values)
            else:
                query = util.build_filter_query(key, values)
                self.filter_text(query)

    def filter_random(self, key):
        """Select one random value for the given key"""
        if key == "album" and self.can_filter_albums():
            albums = self.list_albums()
            if albums:
                self.filter_albums([random.choice(albums)])
        elif self.can_filter_tag(key):
            values = self.list(key)
            if values:
                value = random.choice(values)
                self.filter(key, [value])
        elif self.can_filter_text():
            values = self.list(key)
            if values:
                value = random.choice(values)
                query = util.build_filter_query(key, [value])
                self.filter_text(query)


class Browser(Gtk.Box, Filter):
    """Browsers are how the audio library is presented to the user; they
    create the list of songs that MainSongList is filled with, and pass
    them back via a callback function.
    """

    __gsignals__ = {
        'songs-selected':
        (GObject.SignalFlags.RUN_LAST, None, (object, object)),
        'songs-activated': (GObject.SignalFlags.RUN_LAST, None, ()),
        'uri-received': (GObject.SignalFlags.RUN_LAST, None, (str,))
    }

    name = _("Library Browser")
    """The browser's name, without an accelerator."""

    accelerated_name = _("Library Browser")
    """The name, with an accelerator."""

    keys = ["Unknown"]
    """Keys which are used to reference the browser from the command line.
    The first is the primary one.
    """

    priority = 100
    """Priority in the menu list (0 is first, higher numbers come later)"""

    uses_main_library = True
    """Whether the browser has the main library as source"""

    def songs_selected(self, songs, is_sorted=False):
        """Emits the songs-selected signal.

        If is_sorted is True the songs will be put as is in the song list.
        In case it's False the songs will be sorted by the song list depending
        on its current sort configuration.
        """

        self.emit("songs-selected", songs, is_sorted)

    def songs_activated(self):
        """Call after calling songs_selected() to activate the songs
        (start playing, enqueue etc..)
        """

        self.emit("songs-activated")

    def pack(self, songpane):
        """For custom packing, define a function that returns a Widget with the
        browser and MainSongList both packed into it.
        """
        raise NotImplementedError

    def unpack(self, container, songpane):
        """Unpack the browser and songlist when switching browsers in the main
        window. The container will be automatically destroyed afterwards.
        """
        raise NotImplementedError

    background = True
    """If true, the global filter will be applied by MainSongList to
    the songs returned.
    """

    headers = None
    """A list of column headers to display; None means all are okay."""

    @classmethod
    def init(klass, library):
        """Called after library and MainWindow initialization, before the
        GTK main loop starts.
        """
        pass

    def save(self):
        """Save the selected songlist. Browsers should save whatever
        they need to recreate the criteria for the current song list (not
        the list itself).
        """
        raise NotImplementedError

    def restore(self):
        """Restore the selected songlist. restore is called at startup if the
        browser is the first loaded.
        """
        raise NotImplementedError

    def finalize(self, restored):
        """Called after restore/activate or after the browser is loaded.
        restored is True if restore was called."""
        pass

    def scroll(self, song):
        """Scroll to something related to the given song."""
        pass

    def activate(self):
        """Do whatever is needed to emit songs-selected again."""
        raise NotImplementedError

    can_reorder = False
    """If the song list should be reorderable. In case this is True
    every time the song list gets reordered the whole list of songs is
    passed to reordered().
    """

    def reordered(self, songs):
        """In case can_reorder is True and the song list gets reordered
        this gets called with the whole list of songs.
        """

        raise NotImplementedError

    def dropped(self, songs):
        """Called with a list of songs when songs are dropped but the song
        list does not support reordering. This function should return True if
        the drop was successful.
        """

        return False

    def key_pressed(self, event):
        """Gets called with a key pressed event from the song list.
        Should return True if the key was handled.
        """
        return False

    accelerators = None
    """An AccelGroup that is added to / removed from the window where
    the browser is.
    """

    def Menu(self, songs, library, items):
        """This method returns a Gtk.Menu, probably a SongsMenu. After this
        menu is returned the SongList may modify it further.
        """

        return SongsMenu(library, songs, delete=True, items=items)

    def status_text(self, count, time=None):
        tmpl = numeric_phrase("%d song", "%d songs", count)
        return tmpl + " (%s)" % time

    replaygain_profiles = None
    """Replay Gain profiles for this browser."""


class DisplayPatternMixin(object):
    """Allows Browsers customisable item (e.g. album) display patterns"""

    _DEFAULT_PATTERN_TEXT = ""
    """The default pattern to display"""

    _PATTERN_FN = None
    """The filename to save the display pattern under"""

    __pattern = None
    __pattern_text = None

    @classmethod
    def load_pattern(cls):
        """Load the pattern as defined in `_PATTERN_FN`"""
        print_d("Loading pattern from %s" % cls._PATTERN_FN)
        try:
            with open(cls._PATTERN_FN, "r", encoding="utf-8") as f:
                cls.__pattern_text = f.read().rstrip()
        except EnvironmentError as e:
            print_d("Couldn't load pattern for %s (%s), using default." %
                    (cls.__name__, e))
            cls.__pattern_text = cls._DEFAULT_PATTERN_TEXT
        cls.__refresh_pattern()

    @classmethod
    def update_pattern(cls, pattern_text):
        """Saves `pattern_text` to disk (and caches)"""
        if pattern_text == cls.__pattern_text:
            return
        cls.__pattern_text = pattern_text
        cls.__refresh_pattern()
        cls.refresh_all()
        print_d("Saving pattern for %s to %s" %
                (cls.__name__, cls._PATTERN_FN))
        with open(cls._PATTERN_FN, "w", encoding="utf-8") as f:
            f.write(pattern_text + "\n")

    @classmethod
    def __refresh_pattern(cls):
        cls.__pattern = XMLFromMarkupPattern(cls.__pattern_text)

    @property
    def display_pattern(self):
        """The `Pattern` used for formatting entries in this browser"""
        return self.__pattern

    @property
    def display_pattern_text(self):
        """The text of the display pattern
        used for formatting entries in this browser"""
        return self.__pattern_text or self._DEFAULT_PATTERN_TEXT

    @classmethod
    def refresh_all(cls):
        """Refresh the browser's items"""
        pass


class FakeDisplayItem(dict):
    """Like an `AudioFile`, but if the values aren't present in the underlying
    dictionary, it uses the translated tag names as values.
    See also `util.pattern`"""

    def get(self, key, default="", connector=" - "):
        if key[:1] == "~" and '~' in key[1:]:
            return connector.join(map(self.get, util.tagsplit(key)))
        elif key[:1] == "~" and key[-4:-3] == ":":
            func = key[-3:]
            key = key[:-4]
            return "%s<%s>" % (util.tag(key), func)
        elif key in self:
            return self[key]
        return util.tag(key)

    __call__ = get

    def comma(self, key):
        value = self.get(key)
        if isinstance(value, (int, float)):
            return value
        return value.replace("\n", ", ")


class EditDisplayPatternMixin(object):
    """Provides a display Pattern in an editable frame"""

    _PREVIEW_ITEM = None
    """The `FakeItem` (or similar) to use to interpolate into the pattern"""

    _DEFAULT_PATTERN = None
    """The display pattern to use when none is saved"""

    def edit_display_pane(self, browser, frame_title=None):
        """Returns a Pattern edit widget, with preview,
         optionally wrapped in a named Frame"""

        vbox = Gtk.VBox(spacing=6)
        label = Gtk.Label()
        label.set_alignment(0.0, 0.5)
        label.set_padding(6, 6)
        eb = Gtk.EventBox()
        eb.get_style_context().add_class("entry")
        eb.add(label)
        edit = PatternEditBox(self._DEFAULT_PATTERN)
        edit.text = browser.display_pattern_text
        edit.apply.connect('clicked', self._set_pattern, edit, browser)
        connect_obj(
                edit.buffer, 'changed', self._preview_pattern, edit, label)
        vbox.pack_start(eb, False, True, 3)
        vbox.pack_start(edit, True, True, 0)
        self._preview_pattern(edit, label)
        return qltk.Frame(frame_title, child=vbox) if frame_title else vbox

    def _set_pattern(self, button, edit, browser):
        browser.update_pattern(edit.text)

    def _preview_pattern(self, edit, label):
        try:
            text = XMLFromMarkupPattern(edit.text) % self._PREVIEW_ITEM
        except:
            text = _("Invalid pattern")
            edit.apply.set_sensitive(False)
        try:
            Pango.parse_markup(text, -1, u"\u0000")
        except GLib.GError:
            text = _("Invalid pattern")
            edit.apply.set_sensitive(False)
        else:
            edit.apply.set_sensitive(True)
        label.set_markup(text)
