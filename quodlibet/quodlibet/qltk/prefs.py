# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gtk

from quodlibet import config
from quodlibet import const
from quodlibet import player
from quodlibet import qltk
from quodlibet import util

from quodlibet.parse import Query
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.chooser import FolderChooser
from quodlibet.qltk.entry import ValidatingEntry
from quodlibet.qltk.songlist import SongList

class PreferencesWindow(qltk.Window):
    __window = None

    def __new__(klass, parent):
        if klass.__window is None:
            return super(PreferencesWindow, klass).__new__(klass)
        else: return klass.__window

    class SongList(gtk.VBox):
        def __init__(self):
            super(PreferencesWindow.SongList, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Song List")
            vbox = gtk.VBox(spacing=12)
            tips = qltk.Tooltips(self)

            buttons = {}
            table = gtk.Table(3, 3)
            table.set_homogeneous(True)
            checks = config.get("settings", "headers").split()
            for j, l in enumerate(
                [[("~#disc", _("_Disc")),
                  ("album", _("Al_bum")),
                  ("~basename",_("_Filename"))],
                 [("~#track", _("_Track")),
                  ("artist", _("_Artist")),
                  ("~#rating", _("_Rating"))],
                 [("title", util.tag("title")),
                  ("date", _("_Date")),
                  ("~#length",_("_Length"))]]):
                for i, (k, t) in enumerate(l):
                    buttons[k] = gtk.CheckButton(t)
                    if k in checks:
                        buttons[k].set_active(True)
                        checks.remove(k)

                    table.attach(buttons[k], i, i + 1, j, j + 1)

            vbox.pack_start(table, expand=False)

            vbox2 = gtk.VBox()
            tiv = gtk.CheckButton(_("Title includes _version"))
            if "~title~version" in checks:
                buttons["title"].set_active(True)
                tiv.set_active(True)
                checks.remove("~title~version")
            aip = gtk.CheckButton(_("Album includes _part"))
            if "~album~part" in checks:
                buttons["album"].set_active(True)
                aip.set_active(True)
                checks.remove("~album~part")
            fip = gtk.CheckButton(_("Filename includes _folder"))
            if "~filename" in checks:
                buttons["~basename"].set_active(True)
                fip.set_active(True)
                checks.remove("~filename")

            t = gtk.Table(2, 2)
            t.set_homogeneous(True)
            t.attach(tiv, 0, 1, 0, 1)
            t.attach(aip, 0, 1, 1, 2)
            t.attach(fip, 1, 2, 0, 1)
            vbox.pack_start(t, expand=False)

            hbox = gtk.HBox(spacing=6)
            l = gtk.Label(_("_Others:"))
            hbox.pack_start(l, expand=False)
            others = gtk.Entry()
            if "~current" in checks: checks.remove("~current")
            others.set_text(" ".join(checks))
            tips.set_tip(
                others, _("Other columns to display, separated by spaces"))
            l.set_mnemonic_widget(others)
            l.set_use_underline(True)
            hbox.pack_start(others)
            vbox.pack_start(hbox, expand=False)

            apply = gtk.Button(stock=gtk.STOCK_APPLY)
            apply.connect(
                'clicked', self.__apply, buttons, tiv, aip, fip, others)
            b = gtk.HButtonBox()
            b.set_layout(gtk.BUTTONBOX_END)
            b.pack_start(apply)
            vbox.pack_start(b)

            frame = qltk.Frame(_("Visible Columns"), child=vbox)
            self.pack_start(frame, expand=False)
            self.show_all()

        def __apply(self, button, buttons, tiv, aip, fip, others):
            headers = []
            for key in ["~#disc", "~#track", "title", "album", "artist",
                        "date", "~basename", "~#rating", "~#length"]:
                if buttons[key].get_active(): headers.append(key)
            if tiv.get_active():
                try: headers[headers.index("title")] = "~title~version"
                except ValueError: pass
            if aip.get_active():
                try: headers[headers.index("album")] = "~album~part"
                except ValueError: pass
            if fip.get_active():
                try: headers[headers.index("~basename")] = "~filename"
                except ValueError: pass

            headers.extend(others.get_text().split())
            if "~current" in headers: headers.remove("~current")
            headers = [header.lower() for header in headers]
            SongList.set_all_column_headers(headers)

    class Browsers(gtk.VBox):
        def __init__(self):
            super(PreferencesWindow.Browsers, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Browsers")
            tips = qltk.Tooltips(self)
            c = ConfigCheckButton(
                _("Color _search terms"), 'browsers', 'color')
            c.set_active(config.getboolean("browsers", "color"))
            tips.set_tip(
                c, _("Display simple searches in blue, "
                     "advanced ones in green, and invalid ones in red"))
            hb = gtk.HBox(spacing=6)
            l = gtk.Label(_("_Global filter:"))
            l.set_use_underline(True)
            e = ValidatingEntry(Query.is_valid_color)
            e.set_text(config.get("browsers", "background"))
            e.connect('changed', self._entry, 'background', 'browsers')
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            self.pack_start(hb, expand=False)

            f = qltk.Frame(_("Search Library"), child=c)
            self.pack_start(f, expand=False)

        def _entry(self, entry, name, section="settings"):
            config.set(section, name, entry.get_text())

    class Player(gtk.VBox):
        def __init__(self):
            super(PreferencesWindow.Player, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Player")

            tips = qltk.Tooltips(self)
            c = ConfigCheckButton(
                _("_Jump to playing song automatically"), 'settings', 'jump')
            tips.set_tip(c, _("When the playing song changes, "
                              "scroll to it in the song list"))
            c.set_active(config.getboolean("settings", "jump"))
            self.pack_start(c, expand=False)

            c = ConfigCheckButton(
                _("_Replay Gain volume adjustment"), "player", "replaygain")
            c.set_active(config.getboolean("player", "replaygain"))
            self.pack_start(c, expand=False)
            c.connect('toggled', self.__toggled_gain)
            self.show_all()

        def __toggled_gain(self, activator):
            player.playlist.volume = player.playlist.volume

    class Library(gtk.VBox):
        def __init__(self):
            super(PreferencesWindow.Library, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Library")
            hb = gtk.HBox(spacing=6)
            b = qltk.Button(_("_Select"), gtk.STOCK_OPEN)
            e = gtk.Entry()
            e.set_text(util.fsdecode(config.get("settings", "scan")))
            hb.pack_start(e)
            tips = qltk.Tooltips(self)
            tips.set_tip(
                e, _("Songs placed in these folders (separated by ':') "
                     "will be added to your library"))
            hb.pack_start(b, expand=False)
            scandirs = config.get("settings", "scan").split(":")
            if scandirs and os.path.isdir(scandirs[-1]):
                # start with last added directory
                initial = scandirs[-1]
            else:
                initial = const.HOME
            b.connect('clicked', self.__select, e, initial)
            e.connect('changed', self.__changed, 'settings', 'scan')
            f = qltk.Frame(_("Scan _Directories"), child=hb)
            f.get_label_widget().set_mnemonic_widget(e)
            self.pack_start(f, expand=False)

            vbox = gtk.VBox(spacing=6)
            hb = gtk.HBox(spacing=6)
            e = gtk.Entry()
            e.set_text(config.get("editing", "split_on"))
            e.connect('changed', self.__changed, 'editing', 'split_on')
            tips.set_tip(e, _('Separators for splitting tags'))
            l = gtk.Label(_("Split _on:"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            vbox.pack_start(hb, expand=False)

            vb2 = gtk.VBox(spacing=0)
            cb = ConfigCheckButton(
                _("Save ratings and play counts"), "editing", "save_to_songs")
            cb.set_active(config.getboolean("editing", "save_to_songs"))
            vb2.pack_start(cb)
            hb = gtk.HBox(spacing=3)
            lab = gtk.Label(_("_Email:"))
            entry = gtk.Entry()
            tips.set_tip(entry, _("Ratings and play counts will be set for "
                                  "this email address"))
            entry.set_text(config.get("editing", "save_email"))
            entry.connect('changed', self.__changed, 'editing', 'save_email')
            hb.pack_start(lab, expand=False)
            hb.pack_start(entry)
            lab.set_mnemonic_widget(entry)
            lab.set_use_underline(True)
            vb2.pack_start(hb)
            vbox.pack_start(vb2, expand=False)

            cb = ConfigCheckButton(
                _("Show _programmatic tags"), 'editing', 'alltags')
            cb.set_active(config.getboolean("editing", 'alltags'))
            vbox.pack_start(cb, expand=False)
            f = qltk.Frame(_("Tag Editing"), child=vbox)
            self.pack_start(f)
            self.show_all()

        def __select(self, button, entry, initial):
            chooser = FolderChooser(self, _("Select Directories"), initial)
            fns = chooser.run()
            chooser.destroy()
            if fns: entry.set_text(":".join(map(util.fsdecode, fns)))

        def __changed(self, entry, section, name):
            config.set(section, name, entry.get_text())

    def __init__(self, parent):
        if type(self).__window: return
        else: type(self).__window = self
        super(PreferencesWindow, self).__init__()
        self.set_title(_("Quod Libet Preferences"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(qltk.get_top_parent(parent))

        self.add(qltk.Notebook())
        for Page in [self.SongList, self.Browsers, self.Player, self.Library]:
            self.child.append_page(Page())

        self.connect_object('destroy', PreferencesWindow.__destroy, self)
        self.show_all()

    def __destroy(self):
        type(self).__window = None
        config.write(const.CONFIG)


