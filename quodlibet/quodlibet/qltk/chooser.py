# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet.qltk import get_top_parent

# Choose folders and return them when run.
class FolderChooser(Gtk.FileChooserDialog):
    def __init__(self, parent, title, initial_dir=None,
                 action=Gtk.FileChooserAction.SELECT_FOLDER):
        super(FolderChooser, self).__init__(
            title=title, parent=get_top_parent(parent), action=action,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        if initial_dir: self.set_current_folder(initial_dir)
        self.set_local_only(True)
        self.set_select_multiple(True)

    def run(self):
        resp = super(FolderChooser, self).run()
        fns = self.get_filenames()
        if resp == Gtk.ResponseType.OK: return fns
        else: return []

# Choose files and return them when run.
class FileChooser(FolderChooser):
    def __init__(self, parent, title, filter=None, initial_dir=None):
        super(FileChooser, self).__init__(
            parent, title, initial_dir, Gtk.FileChooserAction.OPEN)
        if filter:
            def new_filter(args, realfilter): return realfilter(args[0])
            f = Gtk.FileFilter()
            f.set_name(_("Songs"))
            f.add_custom(Gtk.FILE_FILTER_FILENAME, new_filter, filter)
            self.add_filter(f)
