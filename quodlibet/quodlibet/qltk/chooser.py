# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet.qltk import get_top_parent

# Choose folders and return them when run.
class FolderChooser(gtk.FileChooserDialog):
    def __init__(self, parent, title, initial_dir=None,
                 action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER):
        super(FolderChooser, self).__init__(
            title=title, parent=get_top_parent(parent), action=action,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        if initial_dir: self.set_current_folder(initial_dir)
        self.set_local_only(True)
        self.set_select_multiple(True)

    def run(self):
        resp = super(FolderChooser, self).run()
        fns = self.get_filenames()
        if resp == gtk.RESPONSE_OK: return fns
        else: return []

# Choose files and return them when run.
class FileChooser(FolderChooser):
    def __init__(self, parent, title, filter=None, initial_dir=None):
        super(FileChooser, self).__init__(
            parent, title, initial_dir, gtk.FILE_CHOOSER_ACTION_OPEN)
        if filter:
            def new_filter(args, realfilter): return realfilter(args[0])
            f = gtk.FileFilter()
            f.set_name(_("Songs"))
            f.add_custom(gtk.FILE_FILTER_FILENAME, new_filter, filter)
            self.add_filter(f)
