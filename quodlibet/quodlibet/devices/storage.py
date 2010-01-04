# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import shutil
import gtk
import copy
from glob import glob

from quodlibet import util
from quodlibet import const

from quodlibet.devices._base import Device
from quodlibet.library import SongFileLibrary
from quodlibet.parse import FileFromPattern
from quodlibet.qltk import ConfirmAction

CACHE = os.path.join(const.USERDIR, 'cache')

class StorageDevice(Device):
    protocol = 'storage'

    defaults = {
        'pattern': '<artist>/<album>/<title>',
        'covers': True,
        'unclutter': True,
    }

    __library = None
    __pattern = None

    def __init__(self, backend_id, device_id):
        super(StorageDevice, self).__init__(backend_id, device_id)
        filename = util.escape_filename(device_id)
        self.__library_path = os.path.join(CACHE, filename)
        self.__library_name = device_id

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

        check = gtk.CheckButton()
        check.set_active(self['unclutter'])
        props.append((_("_Remove unused covers and directories"),
            check, 'unclutter'))

        return props

    def list(self, wlb):
        self.__load_library()

        wlb.setup()
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
                _("Overwrite <b>%s</b>?") % util.escape(utarget),
                ).run():
                try:
                    # Remove the current song
                    self.__library.remove([self.__library[target]])
                except KeyError:
                    pass
                model = songlist.get_model()
                for row in model:
                    if row[0]['~filename'] == utarget: model.remove(row.iter)
            else: return False

        try:
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            shutil.copyfile(util.fsencode(song['~filename']), target)

            if self['covers']:
                coverfile = os.path.join(dirname, 'folder.jpg')
                cover = song.find_cover()
                if cover and util.mtime(cover.name) > util.mtime(coverfile):
                    image = gtk.gdk.pixbuf_new_from_file_at_size(
                        cover.name, 200, 200)
                    image.save(coverfile, 'jpeg')

            song = copy.deepcopy(song)
            song.sanitize(target)
            self.__library.add([song])
            return song
        except (OSError, IOError), exc:
            return str(exc).decode(const.ENCODING, 'replace')

    def delete(self, songlist, song):
        try:
            path = song['~filename']
            dir = os.path.dirname(path)

            os.unlink(path)

            if self['unclutter']:
                files = glob(dir+'/*')
                if len(files) == 1 and os.path.isfile(files[0]) and \
                    os.path.basename(files[0]) == 'folder.jpg':
                    os.unlink(files[0])
                try: os.removedirs(os.path.dirname(path))
                except OSError: pass

            return True
        except (OSError, IOError), exc:
            return str(exc).decode(const.ENCODING, 'replace')

    def cleanup(self, wlb, action):
        self.__save_library()
        return True

    def __load_library(self):
        if self.__library is None:
            self.__library = SongFileLibrary(self.__library_name)
            if os.path.isfile(self.__library_path):
                self.__library.load(self.__library_path)

    def __save_library(self):
        self.__library.save(self.__library_path)

devices = [StorageDevice]
