# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import shutil
import copy
from glob import glob

from gi.repository import Gtk, GLib, GdkPixbuf

import quodlibet
from quodlibet import util
from quodlibet import app
from quodlibet import _
from quodlibet.devices._base import Device
from quodlibet.library import SongFileLibrary
from quodlibet.pattern import FileFromPattern
from quodlibet.qltk.msg import ConfirmFileReplace
from quodlibet.util.path import (mtime, escape_filename,
    strip_win32_incompat_from_path)

CACHE = os.path.join(quodlibet.get_user_dir(), 'cache')


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
        filename = escape_filename(device_id)
        self.__library_path = os.path.join(CACHE, filename)
        self.__library_name = device_id

    def __set_pattern(self, widget=None):
        self.__pattern = FileFromPattern(
            os.path.join(self.mountpoint, self['pattern']))

    def Properties(self):
        props = []

        entry = Gtk.Entry()
        entry.set_text(self['pattern'])
        entry.connect_after('changed', self.__set_pattern)
        props.append((_("_Filename pattern:"), entry, 'pattern'))

        check = Gtk.CheckButton()
        check.set_active(self['covers'])
        props.append((_("Copy _album covers"), check, 'covers'))

        check = Gtk.CheckButton()
        check.set_active(self['unclutter'])
        props.append((_("_Remove unused covers and directories"),
            check, 'unclutter'))

        return props

    def list(self, wlb):
        self.__load_library()

        wlb.setup()
        next = self.__library.rebuild([self.mountpoint]).next
        while True:
            if wlb.quit:
                wlb.hide()
                break
            if not wlb.paused:
                try:
                    next()
                except StopIteration:
                    break
            Gtk.main_iteration()

        self.__save_library()
        return self.__library.values()

    def contains(self, song):
        return song in self.__library

    def copy(self, parent_widget, song):
        if not self.__pattern:
            self.__set_pattern()

        target = strip_win32_incompat_from_path(self.__pattern.format(song))
        dirname = os.path.dirname(target)

        if os.path.exists(target):
            dialog = ConfirmFileReplace(parent_widget, target)
            resp = dialog.run()
            if resp == ConfirmFileReplace.RESPONSE_REPLACE:
                try:
                    # Remove the current song
                    self.__library.remove([self.__library[target]])
                except KeyError:
                    pass
            else:
                return False

        try:
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            shutil.copyfile(song['~filename'], target)

            if self['covers']:
                coverfile = os.path.join(dirname, 'folder.jpg')
                cover = app.cover_manager.get_cover(song)
                if cover and mtime(cover.name) > mtime(coverfile):
                    image = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        cover.name, 200, 200)
                    image.savev(coverfile, "jpeg", [], [])

            song = copy.deepcopy(song)
            song.sanitize(target)
            self.__library.add([song])
            return song
        except (OSError, IOError, GLib.GError) as exc:
            encoding = util.get_locale_encoding()
            return str(exc).decode(encoding, 'replace')

    def delete(self, parent_widget, song):
        try:
            path = song['~filename']
            dir = os.path.dirname(path)

            os.unlink(path)
            self.__library.remove([song])

            if self['unclutter']:
                files = glob(dir + '/*')
                if len(files) == 1 and os.path.isfile(files[0]) and \
                        os.path.basename(files[0]) == 'folder.jpg':
                    os.unlink(files[0])
                try:
                    os.removedirs(os.path.dirname(path))
                except OSError:
                    pass

            return True
        except (OSError, IOError) as exc:
            encoding = util.get_locale_encoding()
            return str(exc).decode(encoding, 'replace')

    def cleanup(self, wlb, action):
        self.__save_library()
        return True

    def close(self):
        if self.__library:
            self.__library.destroy()
            self.__library = None

    def __load_library(self):
        if self.__library is None:
            self.__library = SongFileLibrary(self.__library_name)
            if os.path.isfile(self.__library_path):
                self.__library.load(self.__library_path)

    def __save_library(self):
        self.__library.save(self.__library_path)

devices = [StorageDevice]
