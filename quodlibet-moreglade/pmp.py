# Copyright 2004 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gettext
import config
import util
import shutil

_ = gettext.gettext

class error(RuntimeError): pass

# Routines common to all existing PMP drivers
class PMP(object):
    def __init__(self, songs, window):
        self.songs = songs
        self.window = window

    def run(self):
        for i, song in enumerate(self.songs):
            if self.window.step(i + 1, len(self.songs)): break
            self.upload(song)

    def upload(self, song):
        raise error("This PMP driver should never be instantiated!")

# A driver that copies songs from one directory to another; useful
# for the Neuros, iPod, etc.
class CopyPMP(PMP):
    def __init__(self, *args):
        self.base = os.path.expanduser(config.get("pmp", "location"))
        if not self.base:
            raise error(_("Please set your upload directory in the "
                          "Portable Device section of the preferences "
                          "dialog."))
        if not os.path.isdir(args[0].base):
            raise error(_("The target directory (%s) does not exist")%(
                util.escape(self.base)))
        PMP.__init__(*args)

    def upload(self, song):
        filename = song["~filename"]
        basename = song["~basename"]
        dirname = os.path.basename(os.path.dirname(filename))
        target = os.path.join(self.base, dirname, basename)
        if not os.path.isdir(os.path.dirname(target)):
            try: os.mkdir(os.path.dirname(target))
            except OSError: pass
            except:
                raise error(_("Unable to create directory <b>%s</b>.")%(
                    util.escape(dirname)))
        try: shutil.copyfile(filename, target)
        except:
            raise error(_("Unable to copy <b>%s</b>.") % util.escape(filename))

# Special-case the iFP because I have one. :) Make directories and
# upload files.
class IfpPMP(PMP):
    def __init__(*args):
        if os.system("ifp typestring"):
            raise error(_("Unable to contact your iFP device. Check "
                          "that the device is powered on and plugged "
                          "in, and that you have ifp-line "
                          "(http://ifp-driver.sf.net) installed."))
        self.madedir = []
        PMP.__init__(*args)

    def upload(self, song):
        filename = song["~filename"]
        basename = song["~basename"]
        dirname = os.path.basename(os.path.dirname(filename))
        target = os.path.join(dirname, basename)

        # Avoid spurious calls to ifp mkdir; this can take a long time
        # on a noisy USB line.
        if dirname not in self.madedir:
            os.system("ifp mkdir %r> /dev/null 2>/dev/null" % dirname)
            madedir.append(dirname)
        if os.system("ifp upload %r %r > /dev/null" % (filename, target)):
            raise error(_("Unable to upload <b>%s</b>. The device may be "
                          "out of space, or turned off.")%(
                util.escape(filename)))

# Or, let the user specify a command to run.
class GenericPMP(PMP):
    def __init__(self, *args):
        self.command = os.path.expanduser(config.get("pmp", "command"))
        if len(self.command) == 0:
            raise error(_("Please set your upload command in the "
                          "Portable Devices section of the preferences "
                          "dialog."))
        elif not util.iscommand(self.command.split()[0]):
            raise error(_("The upload command <b>%s</b> was not found. "
                          "Please enter a valid command in the Portable "
                          "Devices section of the preferences dialog and "
                          "try again.")%(
                self.command.split()[0]))
            
        PMP.__init__(self, *args)

    def upload(self, song):
        filename = song["~filename"]
        if "%s" in self.command:
            command = self.command.replace("%s", repr(filename))
        else:
            command = "%s %r" % (self.command, filename)
        if os.system(command):
            raise error(_("Execution of <b>%s</b> failed.")%(
                util.escape(command)))

# This should correspond to the order of the drivers in the combobox.
drivers = [None, CopyPMP, GenericPMP, IfpPMP]
