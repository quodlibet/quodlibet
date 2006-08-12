# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import locale
import os
import shutil
import gtk
import copy

import util
import const

from devices._base import Device
from library import SongFileLibrary
from parse import FileFromPattern
from qltk import ConfirmAction
from qltk.entry import ValidatingEntry
from qltk.wlw import WaitLoadWindow

class StorageDevice(Device):
    type = "generic"

    defaults = {
        'pattern': "",
        'covers': True,
    }

    __library = None
    __pattern = None

    def Properties(self):
        props = []

        entry = gtk.Entry()
        entry.set_text(self['pattern'])
        props.append((_("_Filename Pattern:"), entry, 'pattern'))

        check = gtk.CheckButton()
        check.set_active(self['covers'])
        props.append((_("Copy _album covers"), check, 'covers'))

        return props

    def list(self, browser, rescan=False):
        if self.__library and not rescan:
            return self.__library.values()
        elif not self.__library:
            self.__library = SongFileLibrary()

        library = self.__library

        win = WaitLoadWindow(browser, len(library) // 7,
                             _("Scanning your library. "
                               "This may take several minutes.\n\n"
                               "%d songs reloaded\n%d songs removed"),
                             (0, 0))
        iter = 7
        c, r = [], []
        for c, r in library.rebuild():
            if iter == 7:
                if win.step(len(c), len(r)):
                    win.destroy()
                    break
                iter = 0
            iter += 1
        else:
            win.destroy()
            win = WaitLoadWindow(browser, 0,
                                 _("Scanning for new songs and "
                                   "adding them to your library.\n\n"
                                   "%d songs added"), 0)
            a, c, r = [], [], []
            for a, c, r in library.scan([self.mountpoint()]):
                if win.step(len(a)): break
            win.destroy()

        return library.values()

    def copy(self, songlist, song):
        if not self.__pattern:
            self.__pattern = FileFromPattern(
                os.path.join(self.mountpoint(), self['pattern']))

        utarget = self.__pattern.format(song)
        target = util.fsencode(utarget)
        dirname = os.path.dirname(target)

        if os.path.exists(target):
            if ConfirmAction(
                songlist, _("File exists"),
                _("Overwrite the file <b>%s</b>?") % util.escape(utarget),
                ).run():
                # Remove the current song
                try: del self.__library[target]
                except KeyError: pass
                model = songlist.get_model()
                for row in model:
                    if row[0]["~filename"] == utarget: model.remove(row.iter)
            else: return False

        try:
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            shutil.copyfile(util.fsencode(song["~filename"]), target)

            if self['covers']:
                cover = song.find_cover()
                if cover:
                    filename = os.path.join(dirname,
                        os.path.basename(cover.name))
                    if os.path.isfile(filename): os.remove(filename)
                    shutil.copyfile(cover.name, filename)

            song = copy.deepcopy(song)
            song.sanitize(target)
            self.__library[target] = song
            return song
        except IOError, exc:
            return str(exc).decode(locale.getpreferredencoding(), 'replace')

    def cleanup(self, wlw, action):
        self.__pattern = None

devices = [StorageDevice]
