# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gtk
import pango

import const
import qltk

from parse import XMLFromPattern
from qltk.textedit import PatternEdit

class SongInfo(gtk.Label):
    # Translators: Only worry about "by", "Disc", and "Track" below.
    _pattern = _("""\
\\<span weight='bold' size='large'\\><title>\\</span\\><~length| (<~length>)><version|
\\<small\\>\\<b\\><version>\\</b\\>\\</small\\>><~people|
by <~people>><album|
\\<b\\><album>\\</b\\><discnumber| - Disc <discnumber>>\
<part| - \\<b\\><part>\\</b\\>><tracknumber| - Track <tracknumber>>>""")

    __PATTERN_FILENAME = os.path.join(const.USERDIR, "songinfo")

    def __init__(self, watcher, player):
        super(SongInfo, self).__init__()
        self.set_ellipsize(pango.ELLIPSIZE_END)
        self.set_selectable(True)
        self.set_alignment(0.0, 0.0)
        watcher.connect_object('changed', self.__check_change, player)
        player.connect('song-started', self.__check_started)

        self.connect_object('populate-popup', self.__menu, player)

        try: self._pattern = file(self.__PATTERN_FILENAME).read().rstrip()
        except EnvironmentError: pass
        self._compiled = XMLFromPattern(self._pattern)

    def __menu(self, player, menu):
        item = qltk.MenuItem(_("_Edit Display..."), gtk.STOCK_EDIT)
        item.show()
        item.connect_object('activate', self.__edit, player)
        menu.append(item)

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
        if player.song in songs:
            self.__update_info(player)

    def __check_started(self, player, song):
        if player.song is None:
            self.__update_info(player)

    def __update_info(self, player):
        if player.info is not None:
            text = self._compiled % player.info
        else:
            text = "<span size='xx-large'>%s</span>" % _("Not playing")
        self.set_markup(text)
