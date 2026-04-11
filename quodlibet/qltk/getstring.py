# Copyright 2005 Joe Wreschnig, Michael Urman
#           2013, 2015, 2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gdk, GLib

from quodlibet import _
from quodlibet.qltk.window import Dialog
from quodlibet.qltk import Icons
from quodlibet.qltk.entry import UndoEntry


class GetStringDialog(Dialog):
    """Simple dialog to return a string from the user"""

    def __init__(
        self,
        parent,
        title,
        text,
        button_label=None,
        button_icon=Icons.DOCUMENT_OPEN,
        tooltip=None,
    ):
        super().__init__(title=title, transient_for=parent, use_header_bar=True)

        self.set_resizable(True)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(button_label or _("_OK"), button_icon, Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        content_area = self.get_content_area()
        content_area.set_spacing(6)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lab = Gtk.Label(label=text)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        lab.set_line_wrap(True)
        lab.set_justify(Gtk.Justification.CENTER)
        box.append(lab)

        self._val = UndoEntry()
        if tooltip:
            self._val.set_tooltip_text(tooltip)
        self._val.set_max_width_chars(50)
        box.append(self._val)

        content_area.append(box)
        self.get_child().show_all()

    def _read_clipboard_text(self) -> str | None:
        """Read text from the clipboard synchronously using a nested main loop."""
        display = Gdk.Display.get_default()
        if display is None:
            return None
        clipboard = display.get_clipboard()
        result: list[str | None] = [None]
        loop = GLib.MainLoop()

        def on_read_done(clipboard, async_result):
            try:
                result[0] = clipboard.read_text_finish(async_result)
            except Exception:
                pass
            loop.quit()

        clipboard.read_text_async(None, on_read_done)
        loop.run()
        return result[0]

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
            clip_text = self._read_clipboard_text()
            if clip_text is not None:
                clip_text = self._verify_clipboard(clip_text)
            if clip_text is not None:
                text = clip_text

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
        # GTK4: destroy() removed - self cleaned up automatically
        return value
