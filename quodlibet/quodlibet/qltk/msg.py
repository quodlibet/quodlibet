# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet.qltk import get_top_parent

class Message(gtk.MessageDialog):
    """A message dialog that destroys itself after it is run, uses
    markup, and defaults to an 'OK' button."""

    def __init__(
        self, kind, parent, title, description, buttons=gtk.BUTTONS_OK):
        parent = get_top_parent(parent)
        text = ("<span weight='bold' size='larger'>%s</span>\n\n%s"
                % (title, description))
        super(Message, self).__init__(
            parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            kind, buttons)
        self.set_markup(text)

    def run(self, destroy=True):
        resp = super(Message, self).run()
        if destroy: self.destroy()
        return resp

class ConfirmAction(Message):
    """A message dialog that asks a yes/no question."""

    def __init__(self, *args, **kwargs):
        kwargs["buttons"] = gtk.BUTTONS_YES_NO
        super(ConfirmAction, self).__init__(
            gtk.MESSAGE_WARNING, *args, **kwargs)

    def run(self, destroy = True):
        """Returns True if yes was clicked, False otherwise."""
        resp = super(Message, self).run()
        if destroy: self.destroy()
        if resp == gtk.RESPONSE_YES: return True
        else: return False

class CancelRevertSave(gtk.MessageDialog):
    def __init__(self, parent):
        title = _("Discard tag changes?")
        description = _("Tags have been changed but not saved. Save these "
                        "files, or revert and discard changes?")
        text = ("<span weight='bold' size='larger'>%s</span>\n\n%s"
                % (title, description))
        parent = get_top_parent(parent)
        super(CancelRevertSave, self).__init__(
            parent, flags=0, type=gtk.MESSAGE_WARNING,
            buttons=gtk.BUTTONS_NONE)
        self.add_buttons(gtk.STOCK_SAVE, gtk.RESPONSE_YES,
                         gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_REVERT_TO_SAVED, gtk.RESPONSE_NO)
        self.set_default_response(gtk.RESPONSE_NO)
        self.set_markup(text)

    def run(self):
        resp = super(CancelRevertSave, self).run()
        self.destroy()
        return resp

class ErrorMessage(Message):
    """Like Message, but uses an error-indicating picture."""
    def __init__(self, *args, **kwargs):
        super(ErrorMessage, self).__init__(gtk.MESSAGE_ERROR, *args, **kwargs)

class WarningMessage(Message):
    """Like Message, but uses an warning-indicating picture."""
    def __init__(self, *args, **kwargs):
        super(WarningMessage, self).__init__(
            gtk.MESSAGE_ERROR, *args, **kwargs)
