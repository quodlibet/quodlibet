# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig,
#           2009,2012 Christoph Reiter
#                2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import util
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.plugins.songshelpers import is_a_file, each_song
from quodlibet.util.path import iscommand
from quodlibet.qltk import Icons
from quodlibet.util import connect_obj


class BurnCD(SongsMenuPlugin):
    PLUGIN_ID = 'Burn CD'
    PLUGIN_NAME = _('Burn CD')
    PLUGIN_DESC = _('Burns CDs with K3b, Brasero or xfburn.')
    PLUGIN_ICON = Icons.MEDIA_OPTICAL

    plugin_handles = each_song(is_a_file)

    burn_programs = {
        'K3b': ['k3b', '--audiocd'],
        'Brasero': ['brasero', '--audio'],
        'Xfburn': ['xfburn', '--audio-composition'],
    }

    def __init__(self, *args, **kwargs):
        super(BurnCD, self).__init__(*args, **kwargs)
        self.prog_name = None

        items = self.burn_programs.items()
        progs = [(iscommand(x[1][0]), x) for x in items]
        progs.sort(reverse=True)

        submenu = Gtk.Menu()
        for (is_cmd, (name, (cmd, arg))) in progs:
            item = Gtk.MenuItem(label=name)
            if not is_cmd:
                item.set_sensitive(False)
            else:
                connect_obj(item, 'activate', self.__set, name)
            submenu.append(item)
        self.set_submenu(submenu)

    def __set(self, name):
        self.prog_name = name

    def plugin_songs(self, songs):
        if self.prog_name is None:
            return

        cmd, arg = self.burn_programs[self.prog_name]
        util.spawn([cmd, arg] + [song['~filename'] for song in songs])
