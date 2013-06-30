# Copyright 2005 Joe Wreschnig, Michael Urman
#           2013 Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk


from quodlibet import util
from quodlibet.util import trash
from quodlibet.qltk import get_top_parent
from quodlibet.qltk.msg import ErrorMessage, WarningMessage
from quodlibet.qltk.wlw import WaitLoadWindow
from quodlibet.qltk.x import Button, MenuItem, Alignment


class FileListExpander(Gtk.Expander):
    def __init__(self, songs):
        super(FileListExpander, self).__init__(label=_("Files:"))
        self.set_resize_toplevel(True)

        paths = (util.fsdecode(util.unexpand(s("~filename"))) for s in songs)
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

    def __init__(self, parent, songs):
        title = ngettext(
            "Delete %(file_count)d file permanently?",
            "Delete %(file_count)d files permanently?",
            len(songs)) % {
                "file_count": len(songs),
            }

        description = _("The selected songs will be removed from the "
                        "library and their files deleted from disk.")

        super(DeleteDialog, self).__init__(
            get_top_parent(parent),
            title, description,
            buttons=None)

        area = self.get_message_area()
        exp = FileListExpander(songs)
        exp.show()
        area.pack_start(exp, False, True, 0)

        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        delete_button = Button(_("_Delete Files"), Gtk.STOCK_DELETE)
        delete_button.show()
        self.add_action_widget(delete_button, self.RESPONSE_DELETE)
        self.set_default_response(Gtk.ResponseType.CANCEL)


class TrashDialog(WarningMessage):
    RESPONSE_TRASH = 1

    def __init__(self, parent, songs):
        title = ngettext(
            "Move %(file_count)d file to the trash?",
            "Move %(file_count)d files to the trash?",
            len(songs)) % {
                "file_count": len(songs),
            }

        description = _("The selected songs will be removed from the "
                        "library and their files moved to the trash.")

        super(TrashDialog, self).__init__(
            get_top_parent(parent),
            title, description,
            buttons=None)

        area = self.get_message_area()
        exp = FileListExpander(songs)
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
    dialog = TrashDialog(parent, songs)
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


def _do_delete_songs(parent, songs, librarian):
    dialog = DeleteDialog(parent, songs)
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


def trash_songs(parent, songs, librarian):
    if not songs:
        return

    if trash.can_trash():
        _do_trash_songs(parent, songs, librarian)
    else:
        _do_delete_songs(parent, songs, librarian)
