# Copyright 2014-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from gi.repository import Gtk
from senf import uri2fsn, fsnative, fsn2text, path2fsn, bytes2fsn, text2fsn

import quodlibet
from quodlibet import _, print_d
from quodlibet import formats, qltk
from quodlibet.qltk import Icons
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.wlw import WaitLoadWindow
from quodlibet.util import escape
from quodlibet.util.collection import FileBackedPlaylist
from quodlibet.util.path import mkdir, uri_is_valid


# Directory for playlist files
PLAYLISTS = os.path.join(quodlibet.get_data_dir(), "playlists")
assert isinstance(PLAYLISTS, fsnative)
if not os.path.isdir(PLAYLISTS):
    mkdir(PLAYLISTS)


class ConfirmRemovePlaylistDialog(qltk.Message):
    def __init__(self, parent, playlist):
        title = (_("Are you sure you want to delete the playlist '%s'?")
                 % escape(playlist.name))
        description = (_("All information about the selected playlist "
                         "will be deleted and can not be restored."))

        super().__init__(
            Gtk.MessageType.WARNING, parent, title, description,
            Gtk.ButtonsType.NONE)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(_("_Delete"), Icons.EDIT_DELETE,
                             Gtk.ResponseType.YES)


class GetPlaylistName(GetStringDialog):
    def __init__(self, parent):
        super().__init__(
            parent, _("New Playlist"),
            _("Enter a name for the new playlist:"),
            button_label=_("_Add"), button_icon=Icons.LIST_ADD)


def parse_m3u(filelike, pl_name, library=None):
    filenames = []
    for line in filelike:
        line = line.strip()
        if line.startswith(b"#"):
            continue
        __attempt_add(line, filenames)
    return __create_playlist(pl_name, _dir_for(filelike), filenames, library)


def parse_pls(filelike, pl_name, library=None):
    filenames = []
    for line in filelike:
        line = line.strip()
        if not line.lower().startswith(b"file"):
            continue
        fn = line[line.index(b"=") + 1:].strip()
        __attempt_add(fn, filenames)
    return __create_playlist(pl_name, _dir_for(filelike), filenames, library)


def __attempt_add(filename, filenames):
    try:
        filenames.append(bytes2fsn(filename, 'utf-8'))
    except ValueError:
        return


def __create_playlist(name, source_dir, files, library):
    playlist = FileBackedPlaylist.new(PLAYLISTS, name, library=library)
    print_d("Created playlist %s" % playlist)
    songs = []
    win = WaitLoadWindow(
        None, len(files),
        _("Importing playlist.\n\n%(current)d/%(total)d songs added."))
    win.show()
    for i, filename in enumerate(files):
        if not uri_is_valid(filename):
            # Plain filename.
            songs.append(_af_for(filename, library, source_dir))
        else:
            try:
                filename = uri2fsn(filename)
            except ValueError:
                # Who knows! Hand it off to GStreamer.
                songs.append(formats.remote.RemoteFile(filename))
            else:
                # URI-encoded local filename.
                songs.append(_af_for(filename, library, source_dir))
        if win.step():
            break
    win.destroy()
    playlist.extend(list(filter(None, songs)))
    return playlist


def _af_for(filename, library, pl_dir):
    full_path = os.path.join(pl_dir, filename)
    filename = os.path.realpath(full_path)

    af = None
    if library:
        af = library.get_filename(filename)
    if af is None:
        af = formats.MusicFile(filename)
    return af


def _name_for(filename):
    if not filename:
        return _("New Playlist")
    name = os.path.basename(os.path.splitext(filename)[0])
    return fsn2text(path2fsn(name))


def _dir_for(filelike):
    try:
        return os.path.dirname(path2fsn(filelike.name))
    except AttributeError:
        # Probably a URL
        return text2fsn(u'')
