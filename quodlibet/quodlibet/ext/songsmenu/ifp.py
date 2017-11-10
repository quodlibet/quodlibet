# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig
#                2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from quodlibet import _
from quodlibet import util, qltk
from quodlibet.plugins.songshelpers import each_song, is_a_file
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.wlw import WaitLoadWindow


class IFPUpload(SongsMenuPlugin):
    PLUGIN_ID = "Send to iFP"
    PLUGIN_NAME = _("Send to iFP")
    PLUGIN_DESC = _("Uploads songs to an iRiver iFP device.")
    PLUGIN_ICON = Icons.MULTIMEDIA_PLAYER

    plugin_handles = each_song(is_a_file)

    def plugin_songs(self, songs):
        if os.system("ifp typestring"):
            qltk.ErrorMessage(
                None, _("No iFP device found"),
                _("Unable to contact your iFP device. Check "
                  "that the device is powered on and plugged "
                  "in, and that you have ifp-line "
                  "(http://ifp-driver.sf.net) installed.")).run()
            return True
        self.__madedir = []

        w = WaitLoadWindow(
            None, len(songs), _("Uploading %(current)d/%(total)d"))
        w.show()

        for i, song in enumerate(songs):
            if self.__upload(song) or w.step():
                w.destroy()
                return True
        else:
            w.destroy()

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
                None, _("Error uploading"),
                _("Unable to upload <b>%s</b>. The device may be "
                  "out of space, or turned off.") % (
                util.escape(filename))).run()
            return True
