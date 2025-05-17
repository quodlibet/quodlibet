# Copyright 2014-2022 Nick Boultbee
#                2022 TheMelmacian
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from quodlibet import _, print_w, ngettext
from quodlibet import formats
from quodlibet.qltk import Icons
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.msg import ConfirmationPrompt
from quodlibet.qltk.wlw import WaitLoadWindow
from quodlibet.util import escape
from quodlibet.util.path import uri_is_valid
from urllib.response import addinfourl
from senf import uri2fsn, fsn2text, path2fsn, bytes2fsn, text2fsn


def confirm_remove_playlist_dialog_invoke(
    parent, playlist, confirmer_cls=ConfirmationPrompt
):
    """Creates and invokes a confirmation dialog that asks the user whether or not
    to go forth with the deletion of the selected playlist.

    Confirmer needs to accept the arguments for constructing a dialog,
    have a run-method returning a response, and have a RESPONSE_INVOKE
    attribute.

    returns the result of comparing the result of run to RESPONSE_INVOKE
    """
    title = _("Are you sure you want to delete the playlist '%s'?") % escape(
        playlist.name
    )
    description = _(
        "All information about the selected playlist "
        "will be deleted and can not be restored."
    )
    ok_text = _("_Delete")
    ok_icon = Icons.EDIT_DELETE

    dialog = confirmer_cls(parent, title, description, ok_text, ok_icon)
    prompt = dialog.run()
    return prompt == confirmer_cls.RESPONSE_INVOKE


def confirm_dnd_playlist_dialog_invoke(
    parent, songs, target_playlist_name, confirmer_cls=ConfirmationPrompt
):
    """see confirm_remove_playlist_dialog_invoke above, except for
    the action of attempting to extend a playlist with a second
    dragged and dropped playlist.
    """
    title = ngettext(
        'Extend "{pl_name}" with {num} additional track?',
        'Extend "{pl_name}" with {num} additional tracks?',
        len(songs),
    ).format(pl_name=target_playlist_name, num=len(songs))

    description = ""
    ok_text = _("_Add Tracks")

    dialog = confirmer_cls(parent, title, description, ok_text)
    prompt = dialog.run()
    return prompt == confirmer_cls.RESPONSE_INVOKE


class GetPlaylistName(GetStringDialog):
    def __init__(self, parent):
        super().__init__(
            parent,
            _("New Playlist"),
            _("Enter a name for the new playlist:"),
            button_label=_("_Create"),
            button_icon=Icons.DOCUMENT_NEW,
        )


def parse_m3u(filelike, pl_name, songs_lib=None, pl_lib=None):
    filenames = []
    for line in filelike:
        line = line.strip()
        if line.startswith(b"#"):
            continue
        __attempt_add(line, filenames)
    return __create_playlist(pl_name, _dir_for(filelike), filenames, songs_lib, pl_lib)


def parse_pls(filelike, pl_name, songs_lib=None, pl_lib=None):
    filenames = []
    for line in filelike:
        line = line.strip()
        if not line.lower().startswith(b"file"):
            continue
        fn = line[line.index(b"=") + 1 :].strip()
        __attempt_add(fn, filenames)
    return __create_playlist(pl_name, _dir_for(filelike), filenames, songs_lib, pl_lib)


def __attempt_add(filename, filenames):
    try:
        filenames.append(bytes2fsn(filename, "utf-8"))
    except ValueError:
        print_w(f"Ignoring invalid filename {filename!r}")


def __create_playlist(name, source_dir, files, songs_lib, pl_lib):
    songs = []
    win = WaitLoadWindow(
        None, len(files), _("Importing playlist.\n\n%(current)d/%(total)d songs added.")
    )
    win.show()
    for _i, filename in enumerate(files):
        song = None
        if not uri_is_valid(filename):
            # Plain filename.
            song = _af_for(filename, songs_lib, source_dir)
        else:
            try:
                filename = uri2fsn(filename)
            except ValueError:
                # Who knows! Hand it off to GStreamer.
                song = formats.remote.RemoteFile(filename)
            else:
                # URI-encoded local filename.
                song = _af_for(filename, songs_lib, source_dir)

        # Only add existing (not None) files to the playlist.
        # Otherwise multiple errors are thrown when the files are accessed
        # to update the displayed track infos.
        if song is not None:
            songs.append(song)
        elif os.path.exists(filename) or os.path.exists(
            os.path.join(source_dir, filename)
        ):
            print_w(
                f"Can't add file to playlist: Unsupported file format in {filename}"
            )
        else:
            print_w(f"Can't add file to playlist: File not found: {filename}")

        if win.step():
            break
    win.destroy()
    return pl_lib.create_from_songs(songs, title=name)


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
        if isinstance(filelike, addinfourl):
            # if the "filelike" was created via urlopen
            # it is wrapped in an addinfourl object
            return os.path.dirname(path2fsn(filelike.fp.name))
        return os.path.dirname(path2fsn(filelike.name))
    except AttributeError:
        # Probably a URL
        return text2fsn("")
