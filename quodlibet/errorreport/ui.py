# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet import app
from quodlibet.qltk.entry import UndoEntry


def find_active_window():
    """Try to get the active Window, default to the main one"""

    for window in Gtk.Window.list_toplevels():
        if window.is_active():
            return window
    else:
        return app.window


class TextExpander(Gtk.Expander):

    def __init__(self, title, text):
        super(TextExpander, self).__init__(label=title)
        self.set_resize_toplevel(True)

        buf = Gtk.TextBuffer()
        buf.set_text(text)
        tv = Gtk.TextView(buffer=buf, editable=False)
        tv.set_left_margin(6)
        if hasattr(tv, "set_top_margin"):
            tv.set_top_margin(6)
            tv.set_bottom_margin(6)

        label = self.get_label_widget()
        label.props.margin = 4

        win = Gtk.ScrolledWindow()
        win.add(tv)
        win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        win.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        win.set_size_request(-1, 175)
        self.add(win)
        win.show_all()


class ErrorDialog(Gtk.MessageDialog):

    RESPONSE_RESTART = 1
    RESPONSE_SUBMIT = 2
    RESPONSE_BUGREPORT = 3

    def __init__(self, parent, error_text):
        main_text = _("An Error Occurred")
        secondary_text = _(
            "You can ignore this error, but the application might be unstable "
            "until it is restarted. Submitting an error report will only "
            "take a few seconds and would help us a lot.")

        super(ErrorDialog, self).__init__(
            text=main_text, secondary_text=secondary_text)

        self.set_transient_for(parent)
        self.set_modal(True)
        self.add_button(_("Submit Error Report"), self.RESPONSE_SUBMIT)
        self.add_button(_("Restart"), self.RESPONSE_RESTART)
        self.add_button(_("Ignore Error"), Gtk.ResponseType.CANCEL)
        self.set_default_response(Gtk.ResponseType.CANCEL)

        area = self.get_message_area()
        expand = TextExpander(_("Error details:"), error_text)
        area.pack_start(expand, False, True, 0)
        area.show_all()


class SubmitErrorDialog(Gtk.MessageDialog):

    RESPONSE_SUBMIT = 1

    def __init__(self, parent, error_text):
        main_text = _("Submit Error Report")
        secondary_text = _(
            "Various details regarding the error and your system will be send "
            "to a third party online service "
            "(<a href='https://www.sentry.io'>www.sentry.io</a>). You can "
            "review the data before sending it below.")

        secondary_text += u"\n\n"

        secondary_text += _(
            "(optional) Please provide a short description of what happened "
            "when the error occurred:")

        super(SubmitErrorDialog, self).__init__(
            modal=True, text=main_text, secondary_text=secondary_text,
            secondary_use_markup=True)

        self.set_transient_for(parent)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(_("_Send"), self.RESPONSE_SUBMIT)
        self.set_default_response(Gtk.ResponseType.CANCEL)

        area = self.get_message_area()

        self._entry = UndoEntry()
        self._entry.set_placeholder_text(_("Short description…"))
        area.pack_start(self._entry, False, True, 0)

        expand = TextExpander(_("Data to be sent:"), error_text)
        area.pack_start(expand, False, True, 0)
        area.show_all()

        self.get_widget_for_response(Gtk.ResponseType.CANCEL).grab_focus()

    def get_comment(self):
        """Returns the user provided error description

        Returns
            text_Type
        """

        return self._entry.get_text()
