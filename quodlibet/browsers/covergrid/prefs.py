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
        self.set_default_size(420, 380)
        self.set_transient_for(qltk.get_top_parent(browser))
        # Do this config-driven setup at instance-time
        self._PREVIEW_ITEM["~rating"] = format_rating(0.75)
        self.mag_lock = False

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        cb = ConfigCheckButton(_("Show album _text"), "browsers", "album_text")
        cb.set_active(config.getboolean("browsers", "album_text", True))
        cb.connect("toggled", lambda s: browser.toggle_text())
        vbox.prepend(cb)

        cb2 = ConfigCheckButton(
            _('Show "All Albums" Item'), "browsers", "covergrid_all"
        )
        cb2.set_active(config.getboolean("browsers", "covergrid_all", True))
        cb2.connect("toggled", lambda s: browser.toggle_item_all())
        vbox.prepend(cb2)

        cb3 = ConfigCheckButton(_("Wide Mode"), "browsers", "covergrid_wide")
        cb3.set_active(config.getboolean("browsers", "covergrid_wide", False))
        cb3.connect("toggled", lambda s: browser.toggle_wide())
        vbox.prepend(cb3)

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

        vbox.prepend(l)
        vbox.prepend(mag_scale)

        f = qltk.Frame(_("Options"), child=vbox)
        box.prepend(f)

        display_frame = self.edit_display_pane(browser, _("Album Display"))
        box.prepend(display_frame)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        close.connect("clicked", lambda *x: self.destroy())
        b = Gtk.HButtonBox()
        b.set_layout(Gtk.ButtonBoxStyle.END)
        b.prepend(close)

        main_box.prepend(box)
        self.use_header_bar()

        if not self.has_close_button():
            main_box.prepend(b)
        self.add(main_box)

        close.grab_focus()
        self.show_all()
