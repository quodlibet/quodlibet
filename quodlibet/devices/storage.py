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
from qltk.renamefiles import StripWindowsIncompat

CACHE = os.path.join(const.USERDIR, 'cache')

class StorageDevice(Device):
    type = "generic"

    defaults = {
        'pattern': "<artist>/<album>/<title>",
        'covers': True,
    }

    __library = None
    __pattern = None

    def __init__(self, udi):
        super(StorageDevice, self).__init__(udi)
        self.__library_path = os.path.join(CACHE, os.path.basename(udi))

    def __set_pattern(self, widget=None):
        self.__pattern = FileFromPattern(
            os.path.join(self.mountpoint, self['pattern']))

    def Properties(self):
        props = []

        entry = gtk.Entry()
        entry.set_text(self['pattern'])
        entry.connect_after('changed', self.__set_pattern)
        props.append((_("_Filename Pattern:"), entry, 'pattern'))

        check = gtk.CheckButton()
        check.set_active(self['covers'])
        props.append((_("Copy _album covers"), check, 'covers'))

        return props

    def list(self, wlb):
        self.__load_library()

        next = self.__library.rebuild([self.mountpoint], wlb).next
        while True:
            if wlb.quit:
                wlb.hide()
                break
            if not wlb.paused:
                try: next()
                except StopIteration: break
            gtk.main_iteration()

        self.__save_library()
        return self.__library.values()

    def copy(self, songlist, song):
        if not self.__pattern:
            self.__set_pattern()

        utarget = util.strip_win32_incompat(self.__pattern.format(song))
        target = util.fsencode(utarget)
        dirname = os.path.dirname(target)

        if os.path.exists(target):
            if ConfirmAction(
                songlist, _("File exists"),
                _("Overwrite the file <b>%s</b>?") % util.escape(utarget),
                ).run():
                try:
                    # Remove the current song
                    song = self.__library[target]
                    self.__library.remove(song)
                except KeyError:
                    pass
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
            self.__library.add([song])
            return song
        except IOError, exc:
            return str(exc).decode(locale.getpreferredencoding(), 'replace')

    def cleanup(self, wlb, action):
        self.__save_library()
        return True

    def __load_library(self):
        if not self.__library:
            self.__library = SongFileLibrary()
            if os.path.isfile(self.__library_path):
                self.__library.load(self.__library_path)

    def __save_library(self):
        self.__library.save(self.__library_path)

devices = [StorageDevice]
