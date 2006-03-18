# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# An example of a bookmark manager. Making the window look nicer,
# being able to edit bookmarks from it directly, or coping with errors
# is left as an exercise for the reader.

import gobject, gtk
import qltk
from qltk.views import HintedTreeView

class GoToDialog(qltk.Window):
    def __init__(self, songs):
        super(GoToDialog, self).__init__()
        self.set_default_size(350, 250)
        self.set_title(_("Bookmarks"))
        self.set_border_width(12)
        model = gtk.TreeStore(str, object)
        for song in songs:
            iter = model.append(None, row=[song("title"), song])
            for time, name in song.bookmarks:
                model.append(iter, row=[name, time])
        view = gtk.TreeView(model)
        view.set_rules_hint(True)
        view.connect('row-activated', self.__row_activated, model)
        view.expand_all()

        render = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Bookmarks"), render, text=0)
        view.append_column(col)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)

        self.add(sw)
        self.show_all()

    def __row_activated(self, view, path, column, model):
        if len(path) == 1:
            time = 0
            song = model[path][1]
        else:
            time = model[path][1]
            song = model[path[:1]][1]

        from player import playlist as player
        player.go_to(song)
        # Ugly hack to avoid trying to seek before GSt is ready.
        gobject.timeout_add(200, player.seek, time * 1000)
        self.destroy()

class Bookmarks(object):
    PLUGIN_NAME = "Go to Bookmark..."
    PLUGIN_DESC = "List all bookmarks in the selected files."
    PLUGIN_ICON = gtk.STOCK_JUMP_TO
    PLUGIN_VERSION = "0.2"

    plugin_songs = GoToDialog
