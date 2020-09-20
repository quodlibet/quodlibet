# Copyright 2004-2007 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2009-2010 Steven Robertson
#      2012,2013,2016 Nick Boultbee
#           2009-2013 Christoph Reiter
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

PEOPLE
_SOME_PEOPLE = "\n".join([util.tag("artist"), util.tag("performer"),
                         util.tag("composer"), util.tag("arranger"), ])

_EMPTY = _("Songs not in an album")
DEFAULT_PATTERN_TEXT = """[b]<album|<album>|%s>[/b]<date| (<date>)>
[small]<~discs|<~discs> - ><~tracks> - <~long-length>[/small]
<~people>""" % _EMPTY


class Preferences(qltk.UniqueWindow, EditDisplayPatternMixin):
    _DEFAULT_PATTERN = DEFAULT_PATTERN_TEXT

    _PREVIEW_ITEM = FakeDisplayItem({
        "date": "2010-10-31",
        "~length": util.format_time_display(6319),
        "~long-length": util.format_time_long(6319),
        "~tracks": numeric_phrase("%d track", "%d tracks", 5),
        "~discs": numeric_phrase("%d disc", "%d discs", 2),
        "~#rating": 0.75,
        "album": _("An Example Album"),
        "~people": _SOME_PEOPLE + "..."})

    def __init__(self, browser):
        if self.is_not_unique():
            return
        super().__init__()
        self.set_border_width(12)
        self.set_title(_("Album List Preferences"))
        self.set_default_size(420, 380)
        self.set_transient_for(qltk.get_top_parent(browser))
        # Do this config-driven setup at instance-time
        self._PREVIEW_ITEM["~rating"] = format_rating(0.75)

        box = Gtk.VBox(spacing=6)
        vbox = Gtk.VBox(spacing=6)
        cb = ConfigCheckButton(
            _("Show album _covers"), "browsers", "album_covers")
        cb.set_active(config.getboolean("browsers", "album_covers"))
        cb.connect('toggled', lambda s: browser.toggle_covers())
        vbox.pack_start(cb, False, True, 0)

        cb = ConfigCheckButton(
            _("Inline _search includes people"),
            "browsers", "album_substrings")
        cb.set_active(config.getboolean("browsers", "album_substrings"))
        vbox.pack_start(cb, False, True, 0)
        f = qltk.Frame(_("Options"), child=vbox)
        box.pack_start(f, False, True, 12)

        display_frame = self.edit_display_pane(browser, _("Album Display"))
        box.pack_start(display_frame, True, True, 0)

        main_box = Gtk.VBox(spacing=12)
        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
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
