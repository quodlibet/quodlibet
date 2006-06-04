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

    __filename = os.path.join(const.USERDIR, "songinfo")

    def __init__(self, watcher, player):
        super(SongInfo, self).__init__()
        self.set_ellipsize(pango.ELLIPSIZE_END)
        self.set_selectable(True)
        self.set_alignment(0.0, 0.0)
        self.set_direction(gtk.TEXT_DIR_LTR)
        player.connect('song-started', self.__song_started)
        watcher.connect_object('changed', self.__check_change, player)

        self.connect_object('populate-popup', self.__menu, player)

        try: self._pattern = file(self.__filename).read().rstrip()
        except EnvironmentError: pass

    def __menu(self, player, menu):
        item = qltk.MenuItem(_("_Edit Display..."), gtk.STOCK_EDIT)
        item.show()
        item.connect_object('activate', self.__edit, player)
        menu.append(item)

    def __edit(self, player):
        w = PatternEdit(self, SongInfo._pattern)
        w.text = self._pattern
        w.apply.connect_object('clicked', self.__set, w, player)

    def __set(self, edit, player):
        self._pattern = edit.text.rstrip()
        if (self._pattern == SongInfo._pattern):
            try: os.unlink(os.path.join(const.USERDIR, "songinfo"))
            except OSError: pass
        else:
            f = file(os.path.join(const.USERDIR, "songinfo"), "w")
            f.write(self._pattern + "\n")
            f.close()
        self.__song_started(player, player.info)

    def __check_change(self, player, songs):
        if player.song in songs:
            self.__song_started(player, player.info)

    def __song_started(self, activator, song):
        if song: t = XMLFromPattern(self._pattern) % song
        else: t = "<span size='xx-large'>%s</span>" % _("Not playing")
        self.set_markup(t)

