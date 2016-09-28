# -*- coding: utf-8 -*-
# Copyright 2014-2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk
from senf import uri2fsn, fsnative, fsn2text, path2fsn

import quodlibet
from quodlibet import _
from quodlibet import formats, qltk
from quodlibet.qltk import Icons
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.wlw import WaitLoadWindow
from quodlibet.util import escape
from quodlibet.util.collection import FileBackedPlaylist
from quodlibet.util.path import mkdir, uri_is_valid


# Directory for playlist files
PLAYLISTS = os.path.join(quodlibet.get_user_dir(), "playlists")
assert isinstance(PLAYLISTS, fsnative)
if not os.path.isdir(PLAYLISTS):
    mkdir(PLAYLISTS)


class ConfirmRemovePlaylistDialog(qltk.Message):
    def __init__(self, parent, playlist):
        title = (_("Are you sure you want to delete the playlist '%s'?")
                 % escape(playlist.name))
        description = (_("All information about the selected playlist "
                         "will be deleted and can not be restored."))

        super(ConfirmRemovePlaylistDialog, self).__init__(
            Gtk.MessageType.WARNING, parent, title, description,
            Gtk.ButtonsType.NONE)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(_("_Delete"), Icons.EDIT_DELETE,
                             Gtk.ResponseType.YES)


class GetPlaylistName(GetStringDialog):
    def __init__(self, parent):
        super(GetPlaylistName, self).__init__(
            parent, _("New Playlist"),
            _("Enter a name for the new playlist:"),
            button_label=_("_Add"), button_icon=Icons.LIST_ADD)


def parse_m3u(filename, library=None):
    plname = fsn2text(path2fsn(os.path.basename(
        os.path.splitext(filename)[0])))

    filenames = []

    with open(filename, "rb") as h:
        for line in h:
            line = line.strip()
            if line.startswith("#"):
                continue
            else:
                filenames.append(line)
    return __parse_playlist(plname, filename, filenames, library)


def parse_pls(filename, name="", library=None):
    plname = fsn2text(path2fsn(os.path.basename(
        os.path.splitext(filename)[0])))

    filenames = []
    with open(filename) as h:
        for line in h:
            line = line.strip()
            if not line.lower().startswith("file"):
                continue
            else:
                try:
                    line = line[line.index("=") + 1:].strip()
                except ValueError:
                    pass
                else:
                    filenames.append(line)
    return __parse_playlist(plname, filename, filenames, library)


def __parse_playlist(name, plfilename, files, library):
    playlist = FileBackedPlaylist.new(PLAYLISTS, name, library=library)
    songs = []
    win = WaitLoadWindow(
        None, len(files),
        _("Importing playlist.\n\n%(current)d/%(total)d songs added."))
    win.show()
    for i, filename in enumerate(files):
        if not uri_is_valid(filename):
            if os.name == "nt":
                filename = filename.decode("utf-8", "replace")
            # Plain filename.
            filename = os.path.realpath(os.path.join(
                os.path.dirname(plfilename), filename))
            if library and filename in library:
                songs.append(library[filename])
            else:
                songs.append(formats.MusicFile(filename))
        else:
            try:
                filename = uri2fsn(filename)
            except ValueError:
                # Who knows! Hand it off to GStreamer.
                songs.append(formats.remote.RemoteFile(filename))
            else:
                # URI-encoded local filename.
                filename = os.path.realpath(os.path.join(
                    os.path.dirname(plfilename), filename))
                if library and filename in library:
                    songs.append(library[filename])
                else:
                    songs.append(formats.MusicFile(filename))
        if win.step():
            break
    win.destroy()
    playlist.extend(filter(None, songs))
    return playlist
