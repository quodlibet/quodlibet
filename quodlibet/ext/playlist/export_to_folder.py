# Copyright 2017 Didier Villevalois
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet.pattern import FileFromPattern
from quodlibet.plugins import PluginConfig, ConfProp
from quodlibet.plugins.playlist import PlaylistPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.notif import Task
from quodlibet.qltk.window import Dialog
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.util import copool
from quodlibet.util.dprint import print_d

from shutil import copyfile


class ExportToFolderDialog(Dialog):
    """A dialog to collect export settings"""

    def __init__(self, parent, pattern):
        super(ExportToFolderDialog, self).__init__(
            title=_("Export Playlist to Folder"),
            transient_for=parent, use_header_bar=True)

        self.set_default_size(400, -1)
        self.set_resizable(True)
        self.set_border_width(6)
        self.vbox.set_spacing(6)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(_("_Export"), Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        box = Gtk.VBox(spacing=6)

        destination_label = Gtk.Label(_("Destination folder:"))
        destination_label.set_line_wrap(True)
        destination_label.set_xalign(0.0)
        box.pack_start(destination_label, False, False, 0)

        frame = Gtk.Frame()
        self.directory_chooser = Gtk.FileChooserWidget(
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        self.directory_chooser.set_select_multiple(False)
        self.directory_chooser.set_border_width(1)
        frame.add(self.directory_chooser)
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.set_border_width(0)
        box.pack_start(frame, True, True, 0)

        pattern_label = Gtk.Label(_("Filename pattern:"))
        pattern_label.set_line_wrap(True)
        pattern_label.set_xalign(0.0)
        box.pack_start(pattern_label, False, False, 0)

        self.pattern_entry = UndoEntry()
        self.pattern_entry.set_text(pattern)
        box.pack_start(self.pattern_entry, False, False, 0)

        self.vbox.pack_start(box, True, True, 0)

        self.set_response_sensitive(Gtk.ResponseType.OK, False)

        def changed(*args):
            has_directory = self.directory_chooser.get_filename() is not None
            self.set_response_sensitive(Gtk.ResponseType.OK, has_directory)

            pattern_text = self.pattern_entry.get_text()
            has_pattern = bool(pattern_text)
            self.set_response_sensitive(Gtk.ResponseType.OK, has_pattern)

        self.directory_chooser.connect("selection-changed", changed)
        self.pattern_entry.connect("changed", changed)

        self.get_child().show_all()


class Config:
    _config = PluginConfig(__name__)

    DEFAULT_PATTERN = "<artist~title>"

    default_pattern = ConfProp(_config, "default_pattern", DEFAULT_PATTERN)

CONFIG = Config()


class ExportToFolder(PlaylistPlugin):
    PLUGIN_ID = "ExportToFolder"
    PLUGIN_NAME = _(u"Export Playlist to Folder")
    PLUGIN_DESC = \
        _("Exports a playlist by copying files to a folder.")
    PLUGIN_ICON = Icons.FOLDER
    REQUIRES_ACTION = True

    def __copy_songs(self, task, songs, directory, pattern, parent=None):
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
            try:
                self._copy_file(song, directory, i + 1, pattern)
            except OSError as e:
                print_d("Unable to copy file: {}".format(e))
                ErrorMessage(parent,
                        _("Unable to export playlist"),
                        _("Ensure you have write access to the destination.")
                    ).run()
                break
            task.update(float(i) / total)
            yield True
        print_d("Finished export to directory.")
        task.finish()

    def __cancel_copy(self):
        """Tell the copool to stop copying songs"""
        self.__cancel = True

    def _copy_file(self, song, directory, index, pattern):
        filename = song["~filename"]
        print_d("Copying %s." % filename)
        new_name = pattern.format(song)
        copyfile(filename, "%s/%04d - %s" % (directory, index, new_name))

    def plugin_playlist(self, playlist):
        pattern_text = CONFIG.default_pattern
        dialog = ExportToFolderDialog(self.plugin_window, pattern_text)
        if dialog.run() == Gtk.ResponseType.OK:
            directory = dialog.directory_chooser.get_filename()
            pattern = FileFromPattern(dialog.pattern_entry.get_text())

            task = Task("Export", _("Export Playlist to Folder"),
                        stop=self.__cancel_copy)
            copool.add(self.__copy_songs, task,
                       playlist.songs, directory, pattern, self.plugin_window,
                       funcid="export-playlist-folder")

        dialog.destroy()

    @classmethod
    def PluginPreferences(self, parent):
        def changed(entry):
            CONFIG.default_pattern = entry.get_text()

        vbox = Gtk.VBox(spacing=6)

        def create_pattern():
            hbox = Gtk.HBox(spacing=6)
            hbox.set_border_width(6)
            label = Gtk.Label(label=_("Default filename pattern:"))
            hbox.pack_start(label, False, True, 0)
            entry = UndoEntry()
            if CONFIG.default_pattern:
                entry.set_text(CONFIG.default_pattern)
            entry.connect('changed', changed)
            hbox.pack_start(entry, True, True, 0)
            return hbox

        vbox.pack_start(create_pattern(), True, True, 0)

        return vbox
