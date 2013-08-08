# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2011-2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk, Gdk, Pango

from quodlibet import const
from quodlibet import qltk
from quodlibet import browsers
from quodlibet.util.dprint import print_d
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.information import Information
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.qltk.x import SeparatorMenuItem

from quodlibet.parse import XMLFromMarkupPattern
from quodlibet.qltk.textedit import PatternEdit


class SongInfo(Gtk.EventBox):
    _pattern = ("""\
[span weight='bold' size='large']<title>[/span]\
<~length| (<~length>)><version|
[small][b]<version>[/b][/small]><~people|
%(people)s><album|
[b]<album>[/b]<discnumber| - %(disc)s>\
<discsubtitle| - [b]<discsubtitle>[/b]><tracknumber| - %(track)s>>"""
        % {
        # Translators: As in "by Artist Name"
        "people": _("by %s") % "<~people>",
        "disc": _("Disc %s") % "<discnumber>",
        "track": _("Track %s") % "<tracknumber>"
        })

    __PATTERN_FILENAME = os.path.join(const.USERDIR, "songinfo")

    def __init__(self, library, player):
        super(SongInfo, self).__init__()
        self.set_visible_window(False)
        align = Gtk.Alignment(xscale=0.0, xalign=0.0, yscale=0.0, yalign=0.0)
        label = Gtk.Label()
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_selectable(True)
        align.add(label)
        label.set_alignment(0.0, 0.0)
        self._label = label
        library.connect_object('changed', self.__check_change, player)
        player.connect('song-started', self.__check_started)

        label.connect_object('populate-popup', self.__menu, player, library)
        self.connect('button-press-event', self.__create_menu, player, library)

        try:
            self._pattern = file(self.__PATTERN_FILENAME).read().rstrip()
        except EnvironmentError:
            pass
        self._compiled = XMLFromMarkupPattern(self._pattern)
        align.show_all()
        self.add(align)

    def __create_menu(self, widget, event, player, library):
        button = event.button
        if button == Gdk.BUTTON_SECONDARY:
            menu = Gtk.Menu()
            menu.attach_to_widget(widget, None)
            self.__menu(player, menu, library)
            menu.popup(None, None, None, None, button, event.time)
            return True
        return False

    def __menu(self, player, menu, library):
        try:
            # Get a real sub-menu, unless there's no song, in which case an
            # empty one looks more consistent than None
            submenu = (browsers.playlists.Menu([player.song], self)
                       if player.song else Gtk.Menu())
        except AttributeError, e:
            print_d(e)
        else:
            b = qltk.MenuItem(_("_Add to Playlist"), Gtk.STOCK_ADD)
            b.set_sensitive(player.song is not None and player.song.can_add)
            b.set_submenu(submenu)
            b.show_all()
            sep = SeparatorMenuItem()
            menu.prepend(sep)
            sep.show()
            menu.prepend(b)

        # Issue 298 - Rate current playing song
        sep = SeparatorMenuItem()
        menu.prepend(sep)
        sep.show()
        rating = RatingsMenuItem([player.song], library)
        rating.set_sensitive(bool(player.song))
        rating.show()
        menu.prepend(rating)

        item = qltk.MenuItem(_("_Edit Display..."), Gtk.STOCK_EDIT)
        item.show()
        item.connect_object('activate', self.__edit, player)
        menu.append(item)

        sep = SeparatorMenuItem()
        menu.append(sep)
        sep.show()
        props = qltk.MenuItem(_("Edit _Tags"), Gtk.STOCK_PROPERTIES)

        def song_properties_cb(menu_item):
            window = SongProperties(library, [player.info], self)
            window.show()
        props.connect('activate', song_properties_cb)
        props.show()
        props.set_sensitive(bool(player.song))
        menu.append(props)
        info = Gtk.ImageMenuItem(Gtk.STOCK_INFO, use_stock=True)

        def information_cb(menu_item):
            window = Information(library, [player.info], self)
            window.show()
        info.connect('activate', information_cb)
        info.show()
        menu.append(info)
        info.set_sensitive(bool(player.song))

    def __edit(self, player):
        editor = PatternEdit(self, SongInfo._pattern)
        editor.text = self._pattern
        editor.apply.connect_object('clicked', self.__set, editor, player)
        editor.show()

    def __set(self, edit, player):
        self._pattern = edit.text.rstrip()
        if self._pattern == SongInfo._pattern:
            try:
                os.unlink(self.__PATTERN_FILENAME)
            except OSError:
                pass
        else:
            pattern_file = file(os.path.join(const.USERDIR, "songinfo"), "w")
            pattern_file.write(self._pattern + "\n")
            pattern_file.close()
        self._compiled = XMLFromMarkupPattern(self._pattern)
        self.__update_info(player)

    def __check_change(self, player, songs):
        if player.info in songs:
            self.__update_info(player)

    def __check_started(self, player, song):
        self.__update_info(player)

    def __update_info(self, player, last=None):
        last = last or {}
        text = ("<span size='xx-large'>%s</span>" % _("Not playing")
                if player.info is None
                else self._compiled % player.info)

        # some radio streams update way too often and updating the label
        # destroys the text selection
        if text not in last:
            self._label.set_markup(text)
            last.clear()
            last[text] = True
