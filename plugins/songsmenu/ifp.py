# Copyright 2004-2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, gtk, util, qltk
from plugins.songsmenu import SongsMenuPlugin

class IFPUpload(SongsMenuPlugin):
    PLUGIN_NAME = "Send to iFP"
    PLUGIN_DESC = "Upload songs to an iRiver iFP device"
    PLUGIN_VERSION = "0.11"
    PLUGIN_ICON = gtk.STOCK_CONVERT

    def plugin_songs(self, songs):        
        if os.system("ifp typestring"):
            qltk.ErrorMessage(
                None, "No iFP device found",
                "Unable to contact your iFP device. Check "
                 "that the device is powered on and plugged "
                 "in, and that you have ifp-line "
                 "(http://ifp-driver.sf.net) installed.").run()
            return True
        self.__madedir = []

        w = qltk.WaitLoadWindow(
            None, len(songs), "Uploading %d/%d", (0, len(songs)))

        for i, song in enumerate(songs):
            if self.__upload(song) or w.step(i, len(songs)):
                w.destroy()
                return True
        else: w.destroy()

    def __upload(self, song):
        filename = song["~filename"]
        basename = song("~basename")
        dirname = os.path.basename(os.path.dirname(filename))
        target = os.path.join(dirname, basename)

        # Avoid spurious calls to ifp mkdir; this can take a long time
        # on a noisy USB line.
        if dirname not in self.__madedir:
            os.system("ifp mkdir %r> /dev/null 2>/dev/null" % dirname)
            self.__madedir.append(dirname)
        if os.system("ifp upload %r %r > /dev/null" % (filename, target)):
            qltk.ErrorMessage(
                None, "Error uploading",
                "Unable to upload <b>%s</b>. The device may be "
                "out of space, or turned off."%(
                util.escape(filename))).run()
            return True
