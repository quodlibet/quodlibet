# -*- coding: utf-8 -*-
# Copyright 2014-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk
from senf import uri2fsn, fsnative, fsn2text, path2fsn, bytes2fsn

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
    pl_name = _name_for(filename)

    filenames = []

    with open(filename, "rb") as h:
        for line in h:
            line = line.strip()
            if line.startswith(b"#"):
                continue
            else:
                try:
                    filenames.append(bytes2fsn(line, "utf-8"))
                except ValueError:
                    continue
    return __create_playlist(pl_name, filename, filenames, library)


def parse_pls(filename, library=None):
    pl_name = _name_for(filename)

    filenames = []
    with open(filename, "rb") as h:
        for line in h:
            line = line.strip()
            if not line.lower().startswith(b"file"):
                continue
            else:
                try:
                    line = line[line.index(b"=") + 1:].strip()
                except ValueError:
                    pass
                else:
                    try:
                        filenames.append(bytes2fsn(line, "utf-8"))
                    except ValueError:
                        continue
    return __create_playlist(pl_name, filename, filenames, library)


def __create_playlist(name, pl_filename, files, library):
    playlist = FileBackedPlaylist.new(PLAYLISTS, name, library=library)
    songs = []
    win = WaitLoadWindow(
        None, len(files),
        _("Importing playlist.\n\n%(current)d/%(total)d songs added."))
    win.show()
    for i, filename in enumerate(files):
        if not uri_is_valid(filename):
            # Plain filename.
            songs.append(_af_for(filename, library, pl_filename))
        else:
            try:
                filename = uri2fsn(filename)
            except ValueError:
                # Who knows! Hand it off to GStreamer.
                songs.append(formats.remote.RemoteFile(filename))
            else:
                # URI-encoded local filename.
                songs.append(_af_for(filename, library, pl_filename))
        if win.step():
            break
    win.destroy()
    playlist.extend(filter(None, songs))
    return playlist


def _af_for(filename, library, pl_filename):
    full_path = os.path.join(os.path.dirname(pl_filename), filename)
    filename = os.path.realpath(full_path)
    if library:
        try:
            return library[filename]
        except KeyError:
            pass
    return formats.MusicFile(filename)


def _name_for(filename):
    if not filename:
        return _("New Playlist")
    name = os.path.basename(os.path.splitext(filename)[0])
    return fsn2text(path2fsn(name))
