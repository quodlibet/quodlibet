# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gtk, pango
import const
import qltk
import util
from qltk.textedit import PatternEdit
from parse import XMLFromPattern

class SongInfo(gtk.Label):
    # Translators: Only worry about "by", "Disc", and "Track" below.
    _pattern = _("""\
\\<span weight='bold' size='large'\\><title>\\</span\\><~length| (<~length>)><version|
\\<small\\>\\<b\\><version>\\</b\\>\\</small\\>><~people|
by <~people>><album|
\\<b\\><album>\\</b\\><discnumber| - Disc <discnumber>>\
<part| - \\<b\\><part>\\</b\\>><tracknumber| - Track <tracknumber>>>""")

    __filename = os.path.join(const.DIR, "songinfo")

    def __init__(self, watcher, playlist):
        gtk.Label.__init__(self)
        self.set_ellipsize(pango.ELLIPSIZE_END)
        self.set_selectable(True)
        self.set_alignment(0.0, 0.0)
        self.set_direction(gtk.TEXT_DIR_LTR)
        watcher.connect('song-started', self.__song_started)
        watcher.connect('changed', self.__check_change, playlist)

        self.connect_object(
            'populate-popup', self.__menu, watcher, playlist)

        try: self._pattern = file(self.__filename).read().rstrip()
        except EnvironmentError: pass

    def __menu(self, watcher, menu, playlist):
        item = qltk.MenuItem(_("_Edit Display..."), gtk.STOCK_EDIT)
        item.show()
        item.connect_object('activate', self.__edit, watcher, playlist)
        menu.append(item)

    def __edit(self, watcher, playlist):
        w = PatternEdit(self, SongInfo._pattern)
        w.text = self._pattern
        w.apply.connect_object('clicked', self.__set, w, watcher, playlist)

    def __set(self, edit, watcher, playlist):
        self._pattern = edit.text.rstrip()
        if (self._pattern == SongInfo._pattern):
            try: os.unlink(os.path.join(const.DIR, "songinfo"))
            except OSError: pass
        else:
            f = file(os.path.join(const.DIR, "songinfo"), "w")
            f.write(self._pattern + "\n")
            f.close()
        self.__song_started(watcher, playlist.song)

    def __check_change(self, watcher, songs, playlist):
        if playlist.song in songs:
            self.__song_started(watcher, watcher.song)

    def __song_started(self, watcher, song):
        if song: t = XMLFromPattern(self._pattern) % song
        else: t = "<span size='xx-large'>%s</span>" % _("Not playing")
        self.set_markup(t)

