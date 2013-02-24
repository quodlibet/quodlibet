# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2011,2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gtk
import pango

from quodlibet import const
from quodlibet import qltk
from quodlibet import browsers
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.information import Information
from quodlibet.qltk.ratingsmenu import RatingsMenuItem

from quodlibet.parse import XMLFromPattern
from quodlibet.qltk.textedit import PatternEdit

class SongInfo(gtk.Label):
    _pattern = """\
\\<span weight='bold' size='large'\\><title>\\</span\\>\
<~length| (<~length>)><version|
\\<small\\>\\<b\\><version>\\</b\\>\\</small\\>><~people|
%(people)s><album|
\\<b\\><album>\\</b\\><discnumber| - %(disc)s>\
<discsubtitle| - \\<b\\><discsubtitle>\\</b\\>><tracknumber| - %(track)s>>"""%{
        # Translators: As in "by Artist Name"
        "people": _("by %s") % "<~people>",
        "disc": _("Disc %s") % "<discnumber>",
        "track": _("Track %s") % "<tracknumber>"
        }

    __PATTERN_FILENAME = os.path.join(const.USERDIR, "songinfo")

    def __init__(self, library, player):
        super(SongInfo, self).__init__()
        self.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self.set_selectable(True)
        self.set_alignment(0.0, 0.0)
        library.connect_object('changed', self.__check_change, player)
        player.connect('song-started', self.__check_started)

        self.connect_object('populate-popup', self.__menu, player, library)

        try: self._pattern = file(self.__PATTERN_FILENAME).read().rstrip()
        except EnvironmentError: pass
        self._compiled = XMLFromPattern(self._pattern)

    def __menu(self, player, menu, library):


        try:
            # Get a real submenu, unless there's no song, in which case an
            # empty one looks more consistent than None
            submenu = (browsers.playlists.Menu([player.song], player)
                       if player.song else gtk.Menu())
        except AttributeError,e:
            print_d(e)
        else:
            b = qltk.MenuItem(_("_Add to Playlist"), gtk.STOCK_ADD)
            b.set_sensitive(player.song is not None and player.song.can_add)
            b.set_submenu(submenu)
            b.show_all()
            sep = gtk.SeparatorMenuItem()
            menu.prepend(sep)
            sep.show()
            menu.prepend(b)

        # Issue 298 - Rate current playing song
        sep = gtk.SeparatorMenuItem()
        menu.prepend(sep)
        sep.show()
        rating = RatingsMenuItem([player.song], library)
        rating.set_sensitive(bool(player.song))
        rating.show()
        menu.prepend(rating)

        item = qltk.MenuItem(_("_Edit Display..."), gtk.STOCK_EDIT)
        item.show()
        item.connect_object('activate', self.__edit, player)
        menu.append(item)

        sep = gtk.SeparatorMenuItem()
        menu.append(sep)
        sep.show()
        props = qltk.MenuItem(_("Edit _Tags"), gtk.STOCK_PROPERTIES)
        props.connect_object(
            'activate', SongProperties, library, [player.song], self)
        props.show()
        props.set_sensitive(bool(player.song))
        menu.append(props)
        info = gtk.ImageMenuItem(gtk.STOCK_INFO)
        info.connect_object(
            'activate', Information, library, [player.song], self)
        info.show()
        menu.append(info)
        info.set_sensitive(bool(player.song))

    def __edit(self, player):
        editor = PatternEdit(self, SongInfo._pattern)
        editor.text = self._pattern
        editor.apply.connect_object('clicked', self.__set, editor, player)

    def __set(self, edit, player):
        self._pattern = edit.text.rstrip()
        if (self._pattern == SongInfo._pattern):
            try: os.unlink(self.__PATTERN_FILENAME)
            except OSError: pass
        else:
            pattern_file = file(os.path.join(const.USERDIR, "songinfo"), "w")
            pattern_file.write(self._pattern + "\n")
            pattern_file.close()
        self._compiled = XMLFromPattern(self._pattern)
        self.__update_info(player)

    def __check_change(self, player, songs):
        if player.info in songs:
            self.__update_info(player)

    def __check_started(self, player, song):
        self.__update_info(player)

    def __update_info(self, player, last={}):
        if player.info is not None:
            text = self._compiled % player.info
        else:
            text = "<span size='xx-large'>%s</span>" % _("Not playing")

        # some radio streams update way too often and updating the label
        # destroys the text selection
        if text not in last:
            self.set_markup(text)
            last.clear()
            last[text] = True
