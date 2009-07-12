# Copyright 2009 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# The Unofficial M3U and PLS Specification (Winamp):
# http://forums.winamp.com/showthread.php?threadid=65772

import os
import gtk

from quodlibet import util
from quodlibet import qltk
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.const import HOME as lastfolder

if hasattr(os.path, 'relpath'):
    relpath = os.path.relpath
else:
    # relpath taken from posixpath in Python 2.7
    def relpath(path, start=os.path.curdir):
        """Return a relative version of a path"""

        if not path:
            raise ValueError("no path specified")

        start_list = os.path.abspath(start).split(os.path.sep)
        path_list = os.path.abspath(path).split(os.path.sep)

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return os.path.curdir
        return os.path.join(*rel_list)

class PlaylistExport(SongsMenuPlugin):
    PLUGIN_ID = 'Playlist Export'
    PLUGIN_NAME = _('Playlist Export')
    PLUGIN_DESC = _('Export songs to M3U or PLS playlists.')
    PLUGIN_ICON = 'gtk-save'
    PLUGIN_VERSION = '0.1'

    def plugin_songs(self, songs):
        global lastfolder
        dialog = gtk.FileChooserDialog(self.PLUGIN_NAME,
            None,
            gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)

        ffilter = gtk.FileFilter()
        ffilter.set_name("m3u")
        ffilter.add_mime_type("audio/x-mpegurl")
        ffilter.add_pattern("*.m3u")
        dialog.add_filter(ffilter)

        ffilter = gtk.FileFilter()
        ffilter.set_name("pls")
        ffilter.add_mime_type("audio/x-scpls")
        ffilter.add_pattern("*.pls")
        dialog.add_filter(ffilter)

        dialog.set_current_folder(lastfolder)

        diag_cont = dialog.get_content_area()
        hbox_path = gtk.HBox()
        combo_path = gtk.combo_box_new_text()
        hbox_path.pack_end(combo_path, False, False, padding=6)
        diag_cont.pack_start(hbox_path, False, False)
        diag_cont.show_all()

        map(combo_path.append_text, [_("Relative path"), _("Absolute path")])
        combo_path.set_active(0)

        response = dialog.run()

        if response == gtk.RESPONSE_OK:
            file_path = dialog.get_filename()
            dir_path = os.path.dirname(file_path)

            file_format = dialog.get_filter().get_name()
            extension = "." + file_format
            if not file_path.endswith(extension):
                file_path += extension

            if os.path.exists(file_path) and not qltk.ConfirmAction(
                None,
                _('File exists'),
                _('The file <b>%s</b> already exists.\n\nOverwrite?') %
                util.escape(file_path)).run():
                dialog.destroy()
                return

            relative = combo_path.get_active() == 0

            files = self.__get_files(songs, dir_path, relative)
            if file_format == "m3u":
                self.__m3u_export(file_path, files)
            elif file_format == "pls":
                self.__pls_export(file_path, files)

            lastfolder = dir_path

        dialog.destroy()

    def __get_files(self, songs, dir_path, relative=False):
        files = []
        for song in songs:
            f = {}
            if song.has_key("~uri"):
                f['path'] = song('~filename')
                f['title'] = song("title")
                f['length'] = -1
            else:
                path = song('~filename')
                if relative:
                    path = relpath(path, dir_path)
                f['path'] = path
                f['title'] = "%s - %s" % (
                    song('~people').replace("\n",", "),
                    song('~title~version'))
                f['length'] = song('~#length')
            files.append(f)
        return files

    def __file_error(self, file_path):
        qltk.ErrorMessage(
            None,
            _("Unable to export playlist"),
            _("Writing to <b>%s</b> failed.") % util.escape(file_path)).run()

    def __m3u_export(self, file_path, files):
        try:
            fhandler = open(file_path, "w")
        except IOError:
            self.__file_error(file_path)
        else:
            text = "#EXTM3U\n"

            for f in files:
                text += "#EXTINF:%d,%s\n" % (f['length'], f['title'])
                text += f['path'] + "\n"

            fhandler.write(text.encode("utf-8"))
            fhandler.close()

    def __pls_export(self, file_path, files):
        try:
            fhandler = open(file_path, "w")
        except IOError:
            self.__file_error(file_path)
        else:
            text = "[playlist]\n"

            for num, f in enumerate(files):
                num += 1
                text += "File%d=%s\n" % (num, f['path'])
                text += "Title%d=%s\n" % (num, f['title'])
                text += "Length%d=%s\n" % (num, f['length'])

            text += "NumberOfEntries=%d\n" % len(files)
            text += "Version=2\n"

            fhandler.write(text.encode("utf-8"))
            fhandler.close()
