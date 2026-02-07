# Copyright 2004-2007 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2009-2010 Steven Robertson
#         2012 - 2023 Nick Boultbee
#           2009-2013 Christoph Reiter
#                2016 Mice Pápai
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from gi.repository import Gtk

from quodlibet import config
from quodlibet import qltk
from quodlibet import util
from quodlibet import _
from quodlibet.browsers._base import FakeDisplayItem, EditDisplayPatternMixin
from quodlibet.formats import PEOPLE
from quodlibet.qltk import Button, Icons
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.util import format_rating
from quodlibet.util.i18n import numeric_phrase
from quodlibet.util.dprint import print_d

PEOPLE  # noqa
_SOME_PEOPLE = "\n".join(
    [
        util.tag("artist"),
        util.tag("performer"),
        util.tag("composer"),
        util.tag("arranger"),
    ]
)

_EMPTY = _("Songs not in an album")
DEFAULT_PATTERN_TEXT = f"""[b]<album|<album>|{_EMPTY}>[/b]<date| (<date>)>
[small]<~discs|<~discs> - ><~tracks> - <~long-length>[/small]
<~people>"""


class Preferences(qltk.UniqueWindow, EditDisplayPatternMixin):
    _DEFAULT_PATTERN = DEFAULT_PATTERN_TEXT

    _PREVIEW_ITEM = FakeDisplayItem(
        {
            "date": "2010-10-31",
            "~length": util.format_time_display(6319),
            "~long-length": util.format_time_long(6319),
            "~tracks": numeric_phrase("%d track", "%d tracks", 5),
            "~discs": numeric_phrase("%d disc", "%d discs", 2),
            "~#rating": 0.75,
            "album": _("An Example Album"),
            "~people": _SOME_PEOPLE + "...",
        }
    )

    def __init__(self, browser):
        if self.is_not_unique():
            return
        super().__init__()
        self.set_border_width(12)
        self.set_title(_("Cover Grid Preferences"))
        self.set_default_size(420, 480)
        self.set_transient_for(qltk.get_top_parent(browser))
        # Do this config-driven setup at instance-time
        self._PREVIEW_ITEM["~rating"] = format_rating(0.75)
        self.mag_lock = False

        box = Gtk.VBox(spacing=6)
        vbox = Gtk.VBox(spacing=6)
        cb = ConfigCheckButton(_("Show album _text"), "browsers", "album_text")
        cb.set_active(config.getboolean("browsers", "album_text", True))
        cb.connect("toggled", lambda s: browser.toggle_text())
        vbox.pack_start(cb, False, True, 0)

        cb2 = ConfigCheckButton(
            _('Show "All Albums" Item'), "browsers", "covergrid_all"
        )
        cb2.set_active(config.getboolean("browsers", "covergrid_all", True))
        cb2.connect("toggled", lambda s: browser.toggle_item_all())
        vbox.pack_start(cb2, False, True, 0)

        cb3 = ConfigCheckButton(_("Wide Mode"), "browsers", "covergrid_wide")
        cb3.set_active(config.getboolean("browsers", "covergrid_wide", False))
        cb3.connect("toggled", lambda s: browser.toggle_wide())
        vbox.pack_start(cb3, False, True, 0)

        def mag_changed(mag):
            newmag = mag.get_value()
            oldmag = config.getfloat("browsers", "covergrid_magnification", 3.0)
            if newmag == oldmag:
                print_d(f"Covergrid magnification haven't changed: {newmag}")
                return
            print_d(f"Covergrid magnification update from {oldmag} to {newmag}")
            config.set("browsers", "covergrid_magnification", mag.get_value())
            browser.update_mag()

        mag_scale = Gtk.HScale(
            adjustment=Gtk.Adjustment.new(
                config.getfloat("browsers", "covergrid_magnification", 3),
                1,
                10.0,
                0.5,
                0.5,
                0,
            )
        )
        mag_scale.set_tooltip_text(_("Cover Magnification"))
        l = Gtk.Label(label=_("Cover Magnification"))
        mag_scale.set_value_pos(Gtk.PositionType.RIGHT)
        mag_scale.connect("value-changed", mag_changed)

        vbox.pack_start(l, False, True, 0)
        vbox.pack_start(mag_scale, False, True, 0)

        f = qltk.Frame(_("Options"), child=vbox)
        box.pack_start(f, False, True, 12)

        # Collection Art section
        collection_vbox = Gtk.VBox(spacing=6)

        # Show Collection Art checkbox
        collection_cb = ConfigCheckButton(
            _("Show Collection Art"), "browsers", "covergrid_collection_art"
        )
        collection_cb.set_active(
            config.getboolean("browsers", "covergrid_collection_art", False)
        )

        def on_collection_toggle(widget):
            enabled = widget.get_active()
            collection_dir_box.set_sensitive(enabled)
            if hasattr(browser, "refresh_view"):
                browser.refresh_view()

        collection_cb.connect("toggled", on_collection_toggle)
        collection_vbox.pack_start(collection_cb, False, True, 0)

        # Collection cover directory
        collection_dir_label = Gtk.Label(label=_("Collection cover directory:"))
        collection_dir_label.set_halign(Gtk.Align.START)
        collection_dir_label.set_valign(Gtk.Align.CENTER)
        collection_vbox.pack_start(collection_dir_label, False, True, 0)

        collection_dir_box = Gtk.HBox(spacing=6)
        self.collection_dir_entry = Gtk.Entry()
        current_dir = config.get("browsers", "covergrid_collection_dir", "")
        self.collection_dir_entry.set_text(current_dir)
        self.collection_dir_entry.set_tooltip_text(
            _("Directory containing collection cover images (e.g., 1.jpg, 2.jpg)")
        )

        def on_dir_changed(entry):
            new_dir = entry.get_text()
            config.set("browsers", "covergrid_collection_dir", new_dir)
            if hasattr(browser, "refresh_view"):
                browser.refresh_view()

        self.collection_dir_entry.connect("changed", on_dir_changed)
        collection_dir_box.pack_start(self.collection_dir_entry, True, True, 0)

        # Browse button
        browse_button = Button(_("_Browse"), Icons.FOLDER_OPEN)

        def on_browse_clicked(widget):
            dialog = Gtk.FileChooserDialog(
                title=_("Select Collection Covers Directory"),
                parent=self,
                action=Gtk.FileChooserAction.SELECT_FOLDER,
            )
            dialog.add_buttons(
                _("_Cancel"),
                Gtk.ResponseType.CANCEL,
                _("_Open"),
                Gtk.ResponseType.OK,
            )

            current = self.collection_dir_entry.get_text()
            if current and os.path.exists(current):
                dialog.set_current_folder(current)

            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                folder = dialog.get_filename()
                self.collection_dir_entry.set_text(folder)

            dialog.destroy()

        browse_button.connect("clicked", on_browse_clicked)
        collection_dir_box.pack_start(browse_button, False, True, 0)

        collection_vbox.pack_start(collection_dir_box, False, True, 0)

        # Set initial sensitivity based on checkbox state
        collection_dir_box.set_sensitive(
            config.getboolean("browsers", "covergrid_collection_art", False)
        )

        collection_frame = qltk.Frame(_("Collection Art"), child=collection_vbox)
        box.pack_start(collection_frame, False, True, 6)

        display_frame = self.edit_display_pane(browser, _("Album Display"))
        box.pack_start(display_frame, True, True, 0)

        main_box = Gtk.VBox(spacing=12)
        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        close.connect("clicked", lambda *x: self.destroy())
        b = Gtk.HButtonBox()
        b.set_layout(Gtk.ButtonBoxStyle.END)
        b.pack_start(close, True, True, 0)

        main_box.pack_start(box, True, True, 0)
        self.use_header_bar()

        if not self.has_close_button():
            main_box.pack_start(b, False, True, 0)
        self.add(main_box)

        close.grab_focus()
        self.show_all()
