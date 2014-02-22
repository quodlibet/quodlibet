# Copyright 2005 Joe Wreschnig, Michael Urman
#           2013 Nick Boultbee
#           2013,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""
Functions for deleting files and songs with user interaction.

Only use trash_files() or trash_songs() and TrashMenuItem().
"""

import os

from gi.repository import Gtk

from quodlibet.util import trash
from quodlibet.qltk import get_top_parent
from quodlibet.qltk.msg import ErrorMessage, WarningMessage
from quodlibet.qltk.wlw import WaitLoadWindow
from quodlibet.qltk.x import Button, MenuItem, Alignment
from quodlibet.util.path import fsdecode, unexpand


class FileListExpander(Gtk.Expander):
    """A widget for showing a static list of file paths"""

    def __init__(self, paths):
        super(FileListExpander, self).__init__(label=_("Files:"))
        self.set_resize_toplevel(True)

        paths = [fsdecode(unexpand(p)) for p in paths]
        lab = Gtk.Label("\n".join(paths))
        lab.set_alignment(0.0, 0.0)
        lab.set_selectable(True)
        win = Gtk.ScrolledWindow()
        win.add_with_viewport(Alignment(lab, border=6))
        win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        win.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        win.set_size_request(-1, 100)
        self.add(win)
        win.show_all()


class DeleteDialog(WarningMessage):

    RESPONSE_DELETE = 1
    """"Return value of DeleteDialog.run() in case the passed files
    should be deleted"""

    @classmethod
    def for_songs(cls, parent, songs):
        """Create a delete dialog for deleting songs"""

        description = _("The selected songs will be removed from the "
                        "library and their files deleted from disk.")
        paths = [s("~filename") for s in songs]
        return cls(parent, paths, description)

    @classmethod
    def for_files(cls, parent, paths):
        """Create a delete dialog for deleting files"""

        description = _("The selected files will be deleted from disk.")
        return cls(parent, paths, description)

    def __init__(self, parent, paths, description):
        title = ngettext(
            "Delete %(file_count)d file permanently?",
            "Delete %(file_count)d files permanently?",
            len(paths)) % {
                "file_count": len(paths),
            }

        super(DeleteDialog, self).__init__(
            get_top_parent(parent),
            title, description,
            buttons=Gtk.ButtonsType.NONE)

        area = self.get_message_area()
        exp = FileListExpander(paths)
        exp.show()
        area.pack_start(exp, False, True, 0)

        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        delete_button = Button(_("_Delete Files"), Gtk.STOCK_DELETE)
        delete_button.show()
        self.add_action_widget(delete_button, self.RESPONSE_DELETE)
        self.set_default_response(Gtk.ResponseType.CANCEL)


class TrashDialog(WarningMessage):

    RESPONSE_TRASH = 1
    """"Return value of TrashDialog.run() in case the passed files
    should be moved to the trash"""

    @classmethod
    def for_songs(cls, parent, songs):
        """Create a trash dialog for trashing songs"""

        description = _("The selected songs will be removed from the "
                        "library and their files moved to the trash.")
        paths = [s("~filename") for s in songs]
        return cls(parent, paths, description)

    @classmethod
    def for_files(cls, parent, paths):
        """Create a trash dialog for trashing files"""

        description = _("The selected files will be moved to the trash.")
        return cls(parent, paths, description)

    def __init__(self, parent, paths, description):

        title = ngettext(
            "Move %(file_count)d file to the trash?",
            "Move %(file_count)d files to the trash?",
            len(paths)) % {
                "file_count": len(paths),
            }

        super(TrashDialog, self).__init__(
            get_top_parent(parent),
            title, description,
            buttons=Gtk.ButtonsType.NONE)

        area = self.get_message_area()
        exp = FileListExpander(paths)
        exp.show()
        area.pack_start(exp, False, True, 0)

        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        trash_button = Button(_("_Move to Trash"), "user-trash")
        trash_button.show()
        self.add_action_widget(trash_button, self.RESPONSE_TRASH)
        self.set_default_response(Gtk.ResponseType.CANCEL)


def TrashMenuItem():
    return (MenuItem(_("_Move to Trash"), "user-trash") if trash.can_trash()
            else Gtk.ImageMenuItem(Gtk.STOCK_DELETE, use_stock=True))


def _do_trash_songs(parent, songs, librarian):
    dialog = TrashDialog.for_songs(parent, songs)
    resp = dialog.run()
    if resp != TrashDialog.RESPONSE_TRASH:
        return

    window_title = _("Moving %(current)d/%(total)d.")

    w = WaitLoadWindow(parent, len(songs), window_title)
    w.show()

    ok = []
    failed = []
    for song in songs:
        filename = song("~filename")
        try:
            trash.trash(filename)
        except trash.TrashError:
            failed.append(song)
        else:
            ok.append(song)
        w.step()
    w.destroy()

    if failed:
        ErrorMessage(parent,
            _("Unable to move to trash"),
            _("Moving one or more files to the trash failed.")
        ).run()

    if ok:
        librarian.remove(ok)


def _do_trash_files(parent, paths):
    dialog = TrashDialog.for_files(parent, paths)
    resp = dialog.run()
    if resp != TrashDialog.RESPONSE_TRASH:
        return

    window_title = _("Moving %(current)d/%(total)d.")
    w = WaitLoadWindow(parent, len(paths), window_title)
    w.show()

    ok = []
    failed = []
    for path in paths:
        try:
            trash.trash(path)
        except trash.TrashError:
            failed.append(path)
        else:
            ok.append(path)
        w.step()
    w.destroy()

    if failed:
        ErrorMessage(parent,
            _("Unable to move to trash"),
            _("Moving one or more files to the trash failed.")
        ).run()


def _do_delete_songs(parent, songs, librarian):
    dialog = DeleteDialog.for_songs(parent, songs)
    resp = dialog.run()
    if resp != DeleteDialog.RESPONSE_DELETE:
        return

    window_title = _("Deleting %(current)d/%(total)d.")

    w = WaitLoadWindow(parent, len(songs), window_title)
    w.show()

    ok = []
    failed = []
    for song in songs:
        filename = song("~filename")
        try:
            os.unlink(filename)
        except EnvironmentError:
            failed.append(song)
        else:
            ok.append(song)
        w.step()
    w.destroy()

    if failed:
        ErrorMessage(parent,
            _("Unable to delete files"),
            _("Deleting one or more files failed.")
        ).run()

    if ok:
        librarian.remove(ok)


def _do_delete_files(parent, paths):
    dialog = DeleteDialog.for_files(parent, paths)
    resp = dialog.run()
    if resp != DeleteDialog.RESPONSE_DELETE:
        return

    window_title = _("Deleting %(current)d/%(total)d.")

    w = WaitLoadWindow(parent, len(paths), window_title)
    w.show()

    ok = []
    failed = []
    for path in paths:
        try:
            os.unlink(path)
        except EnvironmentError:
            failed.append(path)
        else:
            ok.append(path)
        w.step()
    w.destroy()

    if failed:
        ErrorMessage(parent,
            _("Unable to delete files"),
            _("Deleting one or more files failed.")
        ).run()


def trash_files(parent, paths):
    """Will try to move the files to the trash,
    or if not possible, delete them permanently.

    Will ask for confirmation in each case.
    """

    if not paths:
        return

    # depends on the platform if we can
    if trash.can_trash():
        _do_trash_files(parent, paths)
    else:
        _do_delete_files(parent, paths)


def trash_songs(parent, songs, librarian):
    """Will try to move the files associated with the songs to the trash,
    or if not possible, delete them permanently.

    Will ask for confirmation in each case.

    The deleted songs will be removed from the librarian.
    """

    if not songs:
        return

    # depends on the platform if we can
    if trash.can_trash():
        _do_trash_songs(parent, songs, librarian)
    else:
        _do_delete_songs(parent, songs, librarian)
