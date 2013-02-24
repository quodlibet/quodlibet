# Copyright 2005 Joe Wreschnig,
#           2009,2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import util
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

    def __init__(self, *args, **kwargs):
        super(BurnCD, self).__init__(*args, **kwargs)
        self.prog_name = None

        items = self.burn_programs.items()
        progs = [(util.iscommand(x[1][0]), x) for x in items]
        progs.sort(reverse=True)

        submenu = gtk.Menu()
        for (is_cmd, (name, (cmd, arg))) in progs:
            item = gtk.MenuItem(name)
            if not is_cmd:
                item.set_sensitive(False)
            else:
                item.connect_object('activate', self.__set, name)
            submenu.append(item)
        self.set_submenu(submenu)

    def __set(self, name):
        self.prog_name = name

    def plugin_songs(self, songs):
        if self.prog_name is None:
            return

        cmd, arg = self.burn_programs[self.prog_name]
        util.spawn([cmd, arg] + [song['~filename'] for song in songs])
