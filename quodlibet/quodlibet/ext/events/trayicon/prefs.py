# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#      2013,2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet import app
from quodlibet import qltk
from quodlibet.util import is_windows
from quodlibet.qltk import Icons
from quodlibet.pattern import Pattern
from quodlibet.qltk.entry import UndoEntry
from .util import pconfig


def supports_scrolling():
    """If our tray icon implementation supports scrolling"""

    return not is_windows()


class Preferences(Gtk.VBox):
    """A small window to configure the tray icon's tooltip."""

    def __init__(self):
        super(Preferences, self).__init__(spacing=12)

        self.set_border_width(6)

        ccb = pconfig.ConfigCheckButton(_("Hide main window on close"),
                                        'window_hide', populate=True)
        self.pack_start(qltk.Frame(_("Behavior"), child=ccb), False, True, 0)

        def on_scroll_changed(button, new_state):
            if button.get_active():
                pconfig.set("modifier_swap", new_state)

        modifier_swap = pconfig.getboolean("modifier_swap")

        scrollwheel_box = Gtk.VBox(spacing=0)
        group = Gtk.RadioButton(
            group=None, label=_("Scroll wheel adjusts volume"),
            use_underline=True)
        group.connect("toggled", on_scroll_changed, False)
        group.set_active(not modifier_swap)
        scrollwheel_box.pack_start(group, False, True, 0)
        group = Gtk.RadioButton(
            group=group, label=_("Scroll wheel changes song"),
            use_underline=True)
        group.connect("toggled", on_scroll_changed, True)
        group.set_active(modifier_swap)
        scrollwheel_box.pack_start(group, False, True, 0)

        if supports_scrolling():
            self.pack_start(
                qltk.Frame(_("Scroll _Wheel"), child=scrollwheel_box),
                True, True, 0)

        box = Gtk.VBox(spacing=6)

        entry_box = Gtk.HBox(spacing=6)

        entry = UndoEntry()
        entry_box.pack_start(entry, True, True, 0)

        def on_reverted(*args):
            pconfig.reset("tooltip")
            entry.set_text(pconfig.gettext("tooltip"))

        revert = Gtk.Button()
        revert.add(Gtk.Image.new_from_icon_name(
            Icons.DOCUMENT_REVERT, Gtk.IconSize.BUTTON))
        revert.connect("clicked", on_reverted)
        entry_box.pack_start(revert, False, True, 0)

        box.pack_start(entry_box, False, True, 0)

        preview = Gtk.Label()
        preview.set_line_wrap(True)
        preview_frame = Gtk.Frame(label=_("Preview"))
        vbox = Gtk.VBox(margin=18)
        vbox.pack_start(preview, False, False, 0)
        preview_frame.add(vbox)
        box.pack_start(preview_frame, False, True, 0)

        tt_frame = qltk.Frame(_("Tooltip Display"), child=box)
        tt_frame.get_label_widget().set_mnemonic_widget(entry)
        self.pack_start(tt_frame, True, True, 0)

        entry.connect('changed', self.__changed_entry, preview, preview_frame)
        entry.set_text(pconfig.gettext("tooltip"))

        for child in self.get_children():
            child.show_all()

    def __changed_entry(self, entry, label, frame):
        text = entry.get_text()

        if app.player.info is None:
            text = _("Not playing")
        else:
            text = Pattern(text) % app.player.info

        label.set_text(text)
        frame.set_tooltip_text(text)
        pconfig.set("tooltip", entry.get_text())
