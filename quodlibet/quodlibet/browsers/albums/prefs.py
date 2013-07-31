# -*- coding: utf-8 -*-
# Copyright 2004-2007 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2009-2010 Steven Robertson
#           2012-2013 Nick Boultbee
#           2009-2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk, GLib, Pango

from quodlibet import config
from quodlibet import qltk
from quodlibet import util
from quodlibet.formats import PEOPLE

from quodlibet.util import gobject_weak, format_rating
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.textedit import PatternEditBox
from quodlibet.parse import XMLFromPattern


EMPTY = _("Songs not in an album")
PATTERN = r"""\<b\><album|<album>|%s>\</b\><date| (<date>)>
\<small\><~discs|<~discs> - ><~tracks> - <~long-length>\</small\>
<~people>""" % EMPTY


class FakeAlbum(dict):
    def get(self, key, default="", connector=" - "):
        if key[:1] == "~" and '~' in key[1:]:
            return connector.join(map(self.get, util.tagsplit(key)))
        elif key[:2] == "~#" and key[-4:-3] == ":":
            func = key[-3:]
            key = key[:-4]
            return "%s<%s>" % (util.tag(key), func)
        elif key in self:
            return self[key]
        return util.tag(key)

    __call__ = get

    def comma(self, key):
        value = self.get(key)
        if isinstance(value, (int, float)):
            return value
        return value.replace("\n", ", ")

PEOPLE
_SOME_PEOPLE = "\n".join([util.tag("artist"), util.tag("performer"),
                         util.tag("composer"), util.tag("arranger"), ])
_EXAMPLE_ALBUM = FakeAlbum({
    "date": "2010-10-31",
    "~length": util.format_time(6319),
    "~long-length": util.format_time_long(6319),
    "~tracks": ngettext("%d track", "%d tracks", 5) % 5,
    "~discs": ngettext("%d disc", "%d discs", 2) % 2,
    "~#rating": 0.75,
    "~rating": format_rating(0.75),
    "album": _("An Example Album"),
    "~people": _SOME_PEOPLE + "..."})


class Preferences(qltk.UniqueWindow):
    def __init__(self, browser):
        if self.is_not_unique():
            return
        super(Preferences, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Album List Preferences") + " - Quod Libet")
        self.set_default_size(420, 380)
        self.set_transient_for(qltk.get_top_parent(browser))

        box = Gtk.VBox(spacing=6)
        vbox = Gtk.VBox(spacing=6)
        cb = ConfigCheckButton(
            _("Show album _covers"), "browsers", "album_covers")
        cb.set_active(config.getboolean("browsers", "album_covers"))
        gobject_weak(cb.connect, 'toggled',
                     lambda s: browser.toggle_covers())
        vbox.pack_start(cb, False, True, 0)

        cb = ConfigCheckButton(
            _("Inline _search includes people"),
            "browsers", "album_substrings")
        cb.set_active(config.getboolean("browsers", "album_substrings"))
        vbox.pack_start(cb, False, True, 0)
        f = qltk.Frame(_("Options"), child=vbox)
        box.pack_start(f, False, True, 12)

        vbox = Gtk.VBox(spacing=6)
        label = Gtk.Label()
        label.set_alignment(0.0, 0.5)
        label.set_padding(6, 6)
        eb = Gtk.EventBox()
        eb.add(label)
        eb.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(58000, 58000, 58000))

        edit = PatternEditBox(PATTERN)
        edit.text = browser._pattern_text
        gobject_weak(edit.apply.connect, 'clicked',
                     self.__set_pattern, edit, browser)
        gobject_weak(edit.buffer.connect_object, 'changed',
                     self.__preview_pattern, edit, label, parent=edit)

        vbox.pack_start(eb, False, True, 3)
        vbox.pack_start(edit, True, True, 0)
        self.__preview_pattern(edit, label)
        f = qltk.Frame(_("Album Display"), child=vbox)
        box.pack_start(f, True, True, 0)

        main_box = Gtk.VBox(spacing=12)
        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        b = Gtk.HButtonBox()
        b.set_layout(Gtk.ButtonBoxStyle.END)
        b.pack_start(close, True, True, 0)

        main_box.pack_start(box, True, True, 0)
        main_box.pack_start(b, False, True, 0)
        self.add(main_box)

        close.grab_focus()
        self.show_all()

    def __set_pattern(self, apply, edit, browser):
        browser.refresh_pattern(edit.text)

    def __preview_pattern(self, edit, label):
        try:
            text = XMLFromPattern(edit.text) % _EXAMPLE_ALBUM
        except:
            text = _("Invalid pattern")
            edit.apply.set_sensitive(False)
        try:
            Pango.parse_markup(text, -1, u"\u0000")
        except GLib.GError:
            text = _("Invalid pattern")
            edit.apply.set_sensitive(False)
        else:
            edit.apply.set_sensitive(True)
        label.set_markup(text)
