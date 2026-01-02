# Copyright 2005 Joe Wreschnig, Michael Urman
#       2021-22 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from gi.repository import Gtk

from quodlibet import _
from quodlibet import util
from quodlibet.qltk import get_top_parent
from quodlibet.qltk.icons import Icons
from quodlibet.qltk.window import Dialog
from quodlibet.util import escape
from senf import fsn2text, path2fsn


class Message(Gtk.MessageDialog, Dialog):
    """A message dialog that destroys itself after it is run, uses
    markup, and defaults to an 'OK' button."""

    def __init__(
        self,
        kind: type,
        parent: Gtk.Widget,
        title: str,
        description: str,
        buttons: Gtk.ButtonsType = Gtk.ButtonsType.OK,
        escape_desc: bool = True,
    ):
        parent = get_top_parent(parent)
        markup = f"<span weight='bold' size='larger'>{escape(title)}</span>\n\n" + (
            escape(description) if escape_desc else description
        )
        super().__init__(
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
            message_type=kind,
            buttons=buttons,
        )
        self.set_markup(markup)

    def run(self, destroy=True):
        resp = super().run()
        if destroy:
            self.destroy()
        return resp


class CancelRevertSave(Gtk.MessageDialog, Dialog):
    def __init__(self, parent):
        title = _("Discard tag changes?")
        description = _(
            "Tags have been changed but not saved. Save these "
            "files, or revert and discard changes?"
        )
        text = f"<span weight='bold' size='larger'>{title}</span>\n\n{description}"
        parent = get_top_parent(parent)
        super().__init__(
            transient_for=parent,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
        )

        self.add_icon_button(_("_Save"), Icons.DOCUMENT_SAVE, Gtk.ResponseType.YES)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(_("_Revert"), Icons.DOCUMENT_REVERT, Gtk.ResponseType.NO)

        self.set_default_response(Gtk.ResponseType.NO)
        self.set_markup(text)

    def run(self):
        resp = super().run()
        self.destroy()
        return resp


class ErrorMessage(Message):
    """Like Message, but uses an error-indicating picture."""

    def __init__(self, *args, **kwargs):
        super().__init__(Gtk.MessageType.ERROR, *args, **kwargs)


class WarningMessage(Message):
    """Like Message, but uses a warning-indicating picture."""

    def __init__(self, *args, **kwargs):
        super().__init__(Gtk.MessageType.WARNING, *args, **kwargs)


class ConfirmationPrompt(WarningMessage):
    """Dialog to confirm actions, given a parent, title, description, and
    OK-button text"""

    RESPONSE_INVOKE = Gtk.ResponseType.YES

    def __init__(
        self,
        parent,
        title,
        description,
        ok_button_text,
        ok_button_icon=Icons.SYSTEM_RUN,
    ):
        super().__init__(parent, title, description, buttons=Gtk.ButtonsType.NONE)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(ok_button_text, ok_button_icon, self.RESPONSE_INVOKE)
        self.set_default_response(Gtk.ResponseType.CANCEL)


class ConfirmFileReplace(WarningMessage):
    RESPONSE_REPLACE = 1

    def __init__(self, parent, path):
        title = _("File exists")
        fn_format = util.bold(fsn2text(path2fsn(path)))
        description = _("Replace %(file-name)s?") % {"file-name": fn_format}

        super().__init__(parent, title, description, buttons=Gtk.ButtonsType.NONE)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(
            _("_Replace File"), Icons.DOCUMENT_SAVE, self.RESPONSE_REPLACE
        )
        self.set_default_response(Gtk.ResponseType.CANCEL)
