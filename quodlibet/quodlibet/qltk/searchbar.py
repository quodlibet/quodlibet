# -*- coding: utf-8 -*-
# Copyright 2010-2011 Christoph Reiter, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gtk
import gobject

from quodlibet import config
from quodlibet import const

from quodlibet.parse import Query
from quodlibet.qltk.cbes import ComboBoxEntrySave
from quodlibet.qltk.x import Button

class SearchBarBox(gtk.HBox):
    """
        A search bar widget for inputting queries.

        signals:
            query-changed - a parsable query string
            focus-out - If the widget gets focused while being focused
                (usually for focusing the songlist)
    """

    __gsignals__ = {
        'query-changed': (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'focus-out': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        }

    timeout = 400

    def __init__(self, filename=None, button=True, completion=None,
            accel_group=None):
        super(SearchBarBox, self).__init__(spacing=6)

        if filename is None:
            filename = os.path.join(const.USERDIR, "lists", "queries")

        combo = ComboBoxEntrySave(filename, count=8,
            validator=Query.is_valid_color, title=_("Saved Searches"),
            edit_title=_("Edit saved searches..."))
        combo.enable_clear_button()

        self.__refill_id = None
        self.__combo = combo
        entry = combo.child
        self.__entry = entry

        if completion:
            entry.set_completion(completion)

        self.connect('destroy', lambda w: w.__remove_timeout())

        self.__sig = combo.connect('changed', self.__text_changed)

        entry.connect('clear', self.__filter_changed)
        entry.connect('backspace', self.__text_changed)
        entry.connect('populate-popup', self.__menu)
        entry.connect('activate', self.__filter_changed)
        entry.connect('activate', self.__save_search)
        entry.connect('focus-out-event', self.__save_search)

        label = gtk.Label(_("_Search:"))
        label.set_use_underline(True)
        label.connect('mnemonic-activate', self.__mnemonic_activate)
        label.set_mnemonic_widget(entry)
        self.pack_start(label, expand=False)

        self.pack_start(combo)

        # search button
        if button:
            search = Button(_("Search"), gtk.STOCK_FIND,
                            size=gtk.ICON_SIZE_MENU)
            search.connect('clicked', self.__filter_changed)
            search.set_tooltip_text(_("Search your library"))
            self.pack_start(search, expand=False)

        if accel_group:
            key, mod = gtk.accelerator_parse("<ctrl>L")
            accel_group.connect_group(key, mod, 0,
                                      lambda *x: label.mnemonic_activate(True))

        self.show_all()

    def __inhibit(self):
        self.__combo.handler_block(self.__sig)

    def __uninhibit(self):
        self.__combo.handler_unblock(self.__sig)

    def set_text(self, text):
        # remove the timeout
        self.__remove_timeout()

        # deactivate all signals and change the entry text
        self.__inhibit()
        self.__entry.set_text(text)
        self.__uninhibit()

    def get_text(self):
        return self.__entry.get_text().decode("utf-8")

    def changed(self):
        """Triggers a filter-changed signal if the current text
        is a parsable query"""
        self.__filter_changed()

    def __menu(self, entry, menu):
        self.Menu(menu)

    def Menu(self, menu):
        """Overwrite this method for altering the menu"""
        pass

    def __mnemonic_activate(self, label, group_cycling):
        widget = label.get_mnemonic_widget()
        if widget.is_focus():
            self.emit('focus-out')
            return True

    def __save_search(self, entry, *args):
        # only save the query on focus-out if eager_search is turned on
        if args and not config.getboolean('settings', 'eager_search'):
            return

        text = entry.get_text().decode('utf-8').strip()
        if text and Query.is_parsable(text):
            # Adding the active text to the model triggers a changed signal
            # (get_active is no longer -1), so inhibit
            self.__inhibit()
            self.__combo.prepend_text(text)
            self.__combo.write()
            self.__uninhibit()

    def __remove_timeout(self):
        if self.__refill_id is not None:
            gobject.source_remove(self.__refill_id)
            self.__refill_id = None

    def __filter_changed(self, *args):
        self.__remove_timeout()

        text = self.__entry.get_text().decode('utf-8')
        if Query.is_parsable(text):
            self.__refill_id = gobject.idle_add(
                self.emit, 'query-changed', text)

    def __text_changed(self, *args):
        # the combobox has an active entry selected -> no timeout
        # todo: we need a timeout when the selection changed because
        # of keyboard input (up/down arrows)
        if self.__combo.get_active() != -1:
            self.__filter_changed()
            return

        if not config.getboolean('settings', 'eager_search'):
            return

        # remove the timeout
        self.__remove_timeout()

        # parse and new timeout
        text = self.__entry.get_text().decode('utf-8')
        if Query.is_parsable(text):
            self.__refill_id = gobject.timeout_add(
                    self.timeout, self.__filter_changed)
