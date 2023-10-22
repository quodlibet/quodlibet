# Copyright 2005 Joe Wreschnig, Michael Urman
#           2013, 2015 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gdk

from quodlibet import _
from quodlibet.qltk.window import Dialog
from quodlibet.qltk import Icons
from quodlibet.qltk.entry import UndoEntry


class GetStringDialog(Dialog):
    """Simple dialog to return a string from the user"""

    def __init__(self, parent, title, text,
                 button_label=_("_OK"), button_icon=Icons.DOCUMENT_OPEN,  # noqa
                 tooltip=None):
        super().__init__(
            title=title, transient_for=parent, use_header_bar=True)

        self.set_border_width(6)
        self.set_resizable(True)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(button_label, button_icon, Gtk.ResponseType.OK)
        self.vbox.set_spacing(6)
        self.set_default_response(Gtk.ResponseType.OK)

        box = Gtk.VBox(spacing=6)
        lab = Gtk.Label(label=text)
        box.set_border_width(6)
        lab.set_line_wrap(True)
        lab.set_justify(Gtk.Justification.CENTER)
        box.pack_start(lab, True, True, 0)

        self._val = UndoEntry()
        if tooltip:
            self._val.set_tooltip_text(tooltip)
        self._val.set_max_width_chars(50)
        box.pack_start(self._val, True, True, 0)

        self.vbox.pack_start(box, True, True, 0)
        self.get_child().show_all()

    def _verify_clipboard(self, text):
        """Return an altered text or None if the content was invalid."""
        return

    def run(self, text="", clipboard=False, test=False):
        """Shows the dialog and returns the entered value.

        If clipboard is set, the initial value will be pulled from the
        clipboard and can be verified/altered by _verify_clipboard. In case the
        verification fails text will be used as fallback"""

        self.show()
        if clipboard:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clip = clipboard.wait_for_text()
            if clip is not None:
                clip = self._verify_clipboard(clip)
            if clip is not None:
                text = clip

        self._val.set_text(text)
        self._val.set_activates_default(True)
        self._val.grab_focus()
        resp = Gtk.ResponseType.OK
        if not test:
            resp = super().run()
        if resp == Gtk.ResponseType.OK:
            value = self._val.get_text()
        else:
            value = None
        self.destroy()
        return value
