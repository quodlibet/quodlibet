# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import util
from qltk import ErrorMessage
from plugins.songsmenu import SongsMenuPlugin

class K3b(SongsMenuPlugin):
    PLUGIN_NAME = 'Burn CD'
    PLUGIN_DESC = 'Burn CDs with K3b.'
    PLUGIN_ICON = 'gtk-cdrom'
    PLUGIN_VERSION = '0.15'

    def plugin_songs(self, songs):
        if not util.iscommand("k3b"):
            ErrorMessage(
                None, "K3b not found",
                "The K3b burning program was not found. "
                "You can get K3b at http://k3b.sourceforge.net.").run()
        else:
            files = [song['~filename'] for song in songs]
            try: util.spawn
            except:
                if len(files) == 1: filelist = "%r" % files[0]
                else: filelist = ("%r " * len(files)) % tuple(files)
                os.system('k3b --audiocd %s &' % filelist)
            else:
                util.spawn(["k3b", "--audiocd", files])
