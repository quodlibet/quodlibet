# -*- coding: utf-8 -*-
# Copyright 2004-2008 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2009,2010 Steven Robertson
#           2009-2013 Christoph Reiter
#           2011,2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GLib

from quodlibet import config
from quodlibet import qltk
from quodlibet import util

from quodlibet.browsers._base import Browser
from quodlibet.formats import PEOPLE
from quodlibet.parse import Query
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.x import ScrolledWindow, Alignment, RPaned
from quodlibet.util.library import background_filter

from .prefs import PreferencesButton
from .util import get_headers
from .pane import Pane


class PanedBrowser(Gtk.VBox, Browser, util.InstanceTracker):
    """A Browser enabling "drilling down" of tracks by successive
    selections in multiple tag pattern panes (e.g. Genre / People / Album ).
    It presents available values (and track counts) for each pane's tag
    """

    __gsignals__ = Browser.__gsignals__

    name = _("Paned Browser")
    accelerated_name = _("_Paned Browser")
    priority = 3

    def pack(self, songpane):
        container = Gtk.HBox()
        self.show()
        container.pack_start(self, True, True, 0)
        self.main_box.pack2(songpane, True, False)
        return container

    def unpack(self, container, songpane):
        self.main_box.remove(songpane)
        container.remove(self)

    @classmethod
    def set_all_wide_mode(klass, value):
        for browser in klass.instances():
            browser.set_wide_mode(value)

    @classmethod
    def set_all_panes(klass):
        for browser in klass.instances():
            browser.refresh_panes()
            browser.fill_panes()

    def __init__(self, library, main):
        super(PanedBrowser, self).__init__()
        self._register_instance()

        self.__main = main

        self._filter = None
        self._library = library
        self.commands = {"query": self.__query}

        self.set_spacing(6)

        completion = LibraryTagCompletion(library.librarian)
        self.accelerators = Gtk.AccelGroup()
        sbb = SearchBarBox(completion=completion,
                           accel_group=self.accelerators)
        sbb.connect('query-changed', self.__text_parse)
        sbb.connect('focus-out', self.__focus)
        self._sb_box = sbb

        align = (Alignment(sbb, left=6, right=6, top=6) if main
                 else Alignment(sbb))
        self.pack_start(align, False, True, 0)

        keyval, mod = Gtk.accelerator_parse("<control>Home")
        s = self.accelerators.connect(keyval, mod, 0, self.__select_all)
        self.connect_object('destroy',
                            self.accelerators.disconnect_key, keyval, mod)
        select = Gtk.Button(_("Select _All"), use_underline=True)
        s = select.connect('clicked', self.__select_all)
        self.connect_object('destroy', select.disconnect, s)
        sbb.pack_start(select, False, True, 0)

        prefs = PreferencesButton(self)
        sbb.pack_start(prefs, False, True, 0)

        for s in [library.connect('changed', self.__changed),
                  library.connect('added', self.__added),
                  library.connect('removed', self.__removed)
                  ]:
            self.connect_object('destroy', library.disconnect, s)

        self.connect('destroy', self.__destroy)

        # contains the panes and the song list
        self.main_box = RPaned()
        self.pack_start(self.main_box, True, True, 0)

        self.refresh_panes()

        for child in self.get_children():
            child.show_all()

    def __destroy(self, *args):
        del self.commands
        del self._sb_box

    def set_wide_mode(self, do_wide):
        hor = Gtk.Orientation.HORIZONTAL
        ver = Gtk.Orientation.VERTICAL
        panes = self.main_box.get_child1()

        if do_wide:
            self.main_box.props.orientation = hor
            panes.props.orientation = ver
        else:
            self.main_box.props.orientation = ver
            panes.props.orientation = hor

    def _get_text(self):
        return self._sb_box.get_text()

    def _set_text(self, text):
        self._sb_box.set_text(text)

    def __query(self, text, library, window, player):
        self.filter_text(text)

    def __focus(self, widget, *args):
        qltk.get_top_parent(widget).songlist.grab_focus()

    def __text_parse(self, bar, text):
        self._set_text(text)
        self.activate()

    def filter_text(self, text):
        self._set_text(text)
        self.activate()

    def __select_all(self, *args):
        self._panes[-1].inhibit()
        for pane in self._panes:
            pane.set_selected(None, True)
        self._panes[-1].uninhibit()
        self._panes[-1].get_selection().emit('changed')

    def __added(self, library, songs):
        songs = filter(self._filter, songs)
        for pane in self._panes:
            pane.add(songs)
            songs = filter(pane.matches, songs)

    def __removed(self, library, songs, remove_if_empty=True):
        songs = filter(self._filter, songs)
        for pane in self._panes:
            pane.remove(songs, remove_if_empty)

    def __changed(self, library, songs):
        self.__removed(library, songs, False)
        self.__added(library, songs)
        self.__removed(library, [])

    def active_filter(self, song):
        # check with the search filter
        if not self._filter(song):
            return False

        # check if the selection is right in every pane
        for pane in self._panes:
            if not pane.matches(song):
                return False

        return True

    def activate(self):
        text = self._get_text()
        if Query.is_parsable(text):
            star = dict.fromkeys(SongList.star)
            star.update(self.__star)
            self._filter = Query(text, star.keys()).search
            songs = filter(self._filter, self._library)
            bg = background_filter()
            if bg:
                songs = filter(bg, songs)
            self._panes[0].fill(songs)

    def scroll(self, song):
        for pane in self._panes:
            pane.scroll(song)

    def refresh_panes(self):
        hbox = self.main_box.get_child1()
        if hbox:
            hbox.destroy()

        hbox = Gtk.HBox(spacing=6)
        hbox.set_homogeneous(True)

        # Fill in the pane list. The last pane reports back to us.
        self._panes = [self]
        for header in reversed(get_headers()):
            pane = Pane(self._library, header, self._panes[0])
            self._panes.insert(0, pane)
        self._panes.pop()  # remove self

        for pane in self._panes:
            if self.__main:
                pane.connect('row-activated',
                             lambda *x: self.emit("activated"))
            sw = ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.set_shadow_type(Gtk.ShadowType.IN)
            sw.add(pane)
            hbox.pack_start(sw, True, True, 0)

        self.main_box.pack1(hbox, True, False)
        hbox.show_all()

        self.__star = {}
        for p in self._panes:
            self.__star.update(dict.fromkeys(p.tags))

        self.set_wide_mode(config.getboolean("browsers", "pane_wide_mode"))

    def fill_panes(self):
        self._panes[-1].inhibit()
        self.activate()
        self._panes[-1].uninhibit()

    def __get_filter_pane(self, key):
        """Get the best pane for filtering etc."""

        canditates = []
        for pane in self._panes:
            if (key in pane.tags or
                    (key in PEOPLE and "~people" in pane.tags)):
                canditates.append((len(pane.tags), pane))
        canditates.sort()
        return (canditates and canditates[0][1]) or None

    def can_filter_tag(self, tag):
        return (self.__get_filter_pane(tag) is not None)

    def can_filter_text(self):
        return True

    def filter(self, tag, values):
        filter_pane = self.__get_filter_pane(tag)

        for pane in self._panes:
            if pane is filter_pane:
                filter_pane.set_selected_by_tag(tag, values, True)
                return
            pane.set_selected([None], True)

    def unfilter(self):
        self._panes[-1].inhibit()
        for pane in self._panes:
            pane.set_selected(None, True)
        self._panes[-1].uninhibit()
        self._set_text("")
        self.activate()

    def list(self, key):
        filter_pane = self.__get_filter_pane(key)

        if filter_pane is None:
            return super(PanedBrowser, self).list(key)

        for pane in self._panes:
            if pane is filter_pane:
                return list(filter_pane.list(key))
            pane.set_selected(None, True)
        return []

    def save(self):
        config.set("browsers", "query_text", self._get_text())

        selected = []
        for pane in self._panes:
            selected.append(pane.get_restore_string())

        to_save = u"\n".join(selected).encode("utf-8")
        config.set("browsers", "pane_selection", to_save)

    def restore(self):
        try:
            text = config.get("browsers", "query_text")
        except config.Error:
            pass
        else:
            self._set_text(text)

        selected = config.get("browsers", "pane_selection")
        if not selected:
            return

        try:
            selected = selected.decode("utf-8")
        except UnicodeDecodeError:
            return

        for pane, string in zip(self._panes, selected.split(u"\n")):
            pane.parse_restore_string(string)

    def finalize(self, restored):
        config.set("browsers", "query_text", "")
        if not restored:
            self.fill_panes()

    def fill(self, songs):
        GLib.idle_add(self.emit, 'songs-selected', list(songs), None)
