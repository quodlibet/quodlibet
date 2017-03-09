# -*- coding: utf-8 -*-
# Copyright 2017 Didier Villevalois
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import _
from quodlibet.plugins.playlist import PlaylistPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.notif import Task
from quodlibet.util import copool
from quodlibet.util.dprint import print_d

import os
from shutil import copyfile


class ExportToFolder(PlaylistPlugin):
    PLUGIN_ID = "ExportToFolder"
    PLUGIN_NAME = _(u"Export Playlist to Folder")
    PLUGIN_DESC = \
        _("Exports a playlist by copying files to a folder.")
    PLUGIN_ICON = Icons.FOLDER
    ELLIPSIZE_NAME = True

    def __copy_songs(self, task, songs, directory):
        """Generator for copool to copy songs to the folder"""
        self.__cancel = False
        total = len(songs)
        print_d("Copying %d song(s) to directory %s. "
                "This might take a while..." % (total, directory))
        for i, song in enumerate(songs):
            if self.__cancel:
                print_d("Cancelled export to directory.")
                self.__cancel = False
                break
            # Actually do the copy
            self._copy_file(song, directory, i)
            task.update(float(i) / total)
            yield True
        print_d("Finished export to directory.")
        task.finish()

    def __cancel_copy(self):
        """Tell the copool to stop copying songs"""
        self.__cancel = True

    def _copy_file(self, song, directory, index):
        filename = song["~filename"]
        print_d("Copying %s." % filename)
        basename = os.path.basename(filename)
        copyfile(filename, "%s/%04d - %s" % (directory, index, basename))

    def plugin_playlist(self, playlist):
        dialog = Gtk.FileChooserDialog(
            _("Select Export Destination Folder"),
            self.plugin_window,
            Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("_Export"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            directory = dialog.get_filename()
            task = Task("Export", _("Export Playlist to Folder"),
                        stop=self.__cancel_copy)
            copool.add(self.__copy_songs, task, playlist.songs, directory,
                       funcid="export-playlist-folder")

        dialog.destroy()
