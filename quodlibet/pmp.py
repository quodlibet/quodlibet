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

class PMP(object):
    def __init__(self, songs, window):
        self.songs = songs
        self.window = window

    def run(self):
        for i, song in enumerate(self.songs):
            self.window.step(i + 1, len(self.songs))
            self.upload(song)

    def upload(self, song):
        raise IOError("This PMP driver should never be instantiated!")

class CopyPMP(PMP):
    def __init__(*args):
        args[0].base = os.path.expanduser(config.get("pmp", "location"))
        if not os.path.isdir(args[0].base):
            raise IOError(_("The target directory (%s) does not exist")%(
                util.escape(args[0].base)))
        PMP.__init__(*args)

    def upload(self, song):
        filename = song["=filename"]
        basename = song["=basename"]
        dirname = os.path.basename(os.path.dirname(filename))
        target = os.path.join(self.base, dirname, basename)
        if not os.path.isdir(os.path.dirname(target)):
            try: os.mkdir(os.path.dirname(target))
            except OSError: pass
            except:
                raise IOError(_("Unable to create directory <b>%s</b>.")%(
                    util.escape(dirname)))
        try: shutil.copyfile(filename, target)
        except:
            raise IOError(_("Unable to copy file <b>%s</b>.")%(
                    util.escape(filename)))

class IfpPMP(PMP):
    def __init__(*args):
        if os.system("ifp typestring") != 0:
            raise IOError(_("Unable to contact your iFP device. Check "
                               "that the device is powered on and plugged "
                               "in, and that you have ifp-line "
                               "(http://ifp-driver.sf.net) installed."))
        PMP.__init__(*args)

    def upload(self, song):
        filename = song["=filename"]
        basename = song["=basename"]
        dirname = os.path.basename(os.path.dirname(filename))
        target = os.path.join(dirname, basename)

        fn_e = filename.replace("\\", "\\\\").replace("'", "\\'")
        target_e = target.replace("\\", "\\\\").replace("'", "\\'")
        dirname_e = dirname.replace("\\", "\\\\").replace("'", "\\'")
        os.system("ifp mkdir '%s' > /dev/null 2>/dev/null" % dirname_e)
        if os.system("ifp upload '%s' '%s' > /dev/null" % (fn_e, target_e)):
            raise IOError(_("Unable to upload <b>%s</b>.")%(
                    util.escape(filename)))

drivers = [None, CopyPMP, IfpPMP]
