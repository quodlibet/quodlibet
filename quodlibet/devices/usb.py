# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gtk

import util
import const

from devices._base import Device
from library import Library
from parse import FileFromPattern
from qltk.entry import ValidatingEntry
from qltk.wlw import WaitLoadWindow

class USBDevice(Device):
    name = _("USB Device")
    description = _("Music players or flash drives which connect over USB")
    icon = os.path.join(const.BASEDIR, "device-usb.png")

    ejectable = True
    writable = True

    mountpoint = ""
    pattern = ""

    __library = None

    def Properties(self, dialog):
        entry = ValidatingEntry(os.path.ismount)
        entry.set_text(self.mountpoint)
        dialog.add_property(_("Mountpoint"), entry, 'mountpoint')

        entry = gtk.Entry()
        entry.set_text(self.pattern)
        dialog.add_property(_("Rename pattern"), entry, 'pattern')

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
                pipe = popen2.Popen4("%s %s" % (prog, self.mountpoint))
                if pipe.wait() == 0: return True
                else: return pipe.fromchild.read()
        else: return _("Unable to find an umount command.")
