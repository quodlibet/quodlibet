# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import shutil
import gtk
import copy
from popen2 import Popen4 as popen

import util
import const

from devices._base import Device
from library import Library
from parse import FileFromPattern
from qltk import ConfirmAction
from qltk.entry import ValidatingEntry
from qltk.wlw import WaitLoadWindow

class StorageDevice(Device):
    name = _("Removable Storage")
    description = _("Any mountable device, such as a USB music player "
                    "or an external hard drive")
    writable = True

    mountpoint = ""
    pattern = ""
    covers = True

    __library = None
    __pattern = None

    # Don't pickle the compiled pattern
    def __getstate__(self):
        self.__pattern = None
        return self.__dict__

    def Properties(self, dialog):
        entry = ValidatingEntry(os.path.ismount)
        entry.set_text(self.mountpoint)
        dialog.add_property(_("_Mount Point:"), entry, 'mountpoint')

        entry = gtk.Entry()
        entry.set_text(self.pattern)
        dialog.add_property(_("_Filename Pattern:"), entry, 'pattern')

        check = gtk.CheckButton()
        check.set_active(self.covers)
        dialog.add_property(_("Copy album covers"), check, 'covers')

    def is_connected(self):
        return os.path.ismount(self.mountpoint)

    def get_space(self):
        info = os.statvfs(self.mountpoint)
        space = info.f_bsize * info.f_blocks
        free = info.f_bsize * info.f_bavail
        return (space, free)

    def list(self, browser, rescan=False):
        if self.__library and not rescan:
            return self.__library.values()
        elif not self.__library:
            self.__library = Library()

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
            for a, c, r in library.scan([self.mountpoint]):
                if win.step(len(a)): break
            win.destroy()

        return library.values()

    def eject(self):
        for prog in ("pumount", "umount"):
            if util.iscommand(prog):
                pipe = popen("%s %s" % (prog, self.mountpoint))
                if pipe.wait() == 0: return True
                else: return pipe.fromchild.read()
        else: return _("No unmounting command was found.")

    def copy(self, songlist, song):
        if not self.__pattern:
            self.__pattern = FileFromPattern(
                os.path.join(self.mountpoint, self.pattern))

        utarget = self.__pattern.format(song)
        target = util.fsencode(utarget)
        dirname = os.path.dirname(target)

        if os.path.exists(target):
            if ConfirmAction(
                songlist, _("File exists"),
                _("Overwrite the file <b>%s</b>?") % util.escape(utarget),
                ).run():
                # Remove the current song
                try: del self.__library[utarget]
                except KeyError: pass
                model = songlist.get_model()
                for row in model:
                    if row[0]["~filename"] == utarget: model.remove(row.iter)
            else: return False

        try:
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            shutil.copyfile(util.fsencode(song["~filename"]), target)

            if self.covers:
                cover = song.find_cover()
                if cover:
                    filename = os.path.join(dirname,
                        os.path.basename(cover.name))
                    if os.path.isfile(filename): os.remove(filename)
                    shutil.copyfile(cover.name, filename)

            song = copy.deepcopy(song)
            song.sanitize(utarget)
            self.__library[utarget] = song
            return song
        except (IOError, Error), exc: return exc.args[-1]

    def cleanup(self, wlw, action):
        self.__pattern = None
