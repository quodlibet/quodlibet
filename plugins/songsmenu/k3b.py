# Copyright 2005 Joe Wreschnig,
#           2009 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import gtk

from quodlibet import util
from quodlibet import config
from quodlibet.qltk import ErrorMessage
from quodlibet.plugins.songsmenu import SongsMenuPlugin

class BurnCD(SongsMenuPlugin):
    PLUGIN_ID = 'Burn CD'
    PLUGIN_NAME = _('Burn CD')
    PLUGIN_DESC = 'Burn CDs with K3b or Brasero.'
    PLUGIN_ICON = 'gtk-cdrom'
    PLUGIN_VERSION = '0.2'

    burn_programs = {
        'K3b': ['k3b', '--audiocd'],
        'Brasero': ['brasero', '--audio']
    }

    try:
        config.get("plugins", __name__)
    except:
        config.set("plugins", __name__, burn_programs.keys()[0])

    def PluginPreferences(klass, window):
        vb = gtk.HBox(spacing=10)
        vb.set_border_width(10)
        label = gtk.Label(_("_Program:"))
        combo = gtk.combo_box_new_text()

        select = 0
        name = config.get("plugins", __name__)
        for i, prog in enumerate(klass.burn_programs.iterkeys()):
            combo.append_text(prog)
            if prog == name:
                select = i

        combo.set_active(select)
        combo.connect('changed',
            lambda e: config.set('plugins', __name__, e.get_active_text()))

        label.set_mnemonic_widget(combo)
        label.set_use_underline(True)
        vb.pack_start(label, expand=False)
        vb.pack_start(combo, expand=False)
        vb.show_all()
        return vb

    PluginPreferences = classmethod(PluginPreferences)

    def plugin_songs(self, songs):
        name = config.get("plugins", __name__)
        prog = self.burn_programs[name]

        if not util.iscommand(prog[0]):
            ErrorMessage(
                None, "%s not found" % name,
                "The %s burning program was not found. " % name).run()
        else:
            files = [song['~filename'] for song in songs]
            util.spawn(prog + files)
