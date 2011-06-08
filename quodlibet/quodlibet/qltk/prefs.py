# -*- coding: utf-8 -*-
# Copyright 2004-2010 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

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
from quodlibet.qltk.entry import ValidatingEntry, UndoEntry
from quodlibet.qltk.songlist import SongList

class PreferencesWindow(qltk.UniqueWindow):
    class SongList(gtk.VBox):
        def __init__(self):
            super(PreferencesWindow.SongList, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Song List")

            c = ConfigCheckButton(
                _("_Jump to playing song automatically"), 'settings', 'jump')
            c.set_tooltip_text(_("When the playing song changes, "
                                 "scroll to it in the song list"))
            c.set_active(config.getboolean("settings", "jump"))
            self.pack_start(c, expand=False)

            vbox = gtk.VBox(spacing=12)

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
            aip = gtk.CheckButton(_("Album includes _disc subtitle"))
            if "~album~discsubtitle" in checks:
                buttons["album"].set_active(True)
                aip.set_active(True)
                checks.remove("~album~discsubtitle")
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
            others = UndoEntry()
            if "~current" in checks: checks.remove("~current")
            others.set_text(" ".join(checks))
            others.set_tooltip_text(
                _("Other columns to display, separated by spaces"))
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
                try: headers[headers.index("album")] = "~album~discsubtitle"
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

            c = ConfigCheckButton(
                _("_Use rounded corners on thumbnails"), 'settings', 'round')
            c.set_tooltip_text(_("Round the corners of album artwork "
                "thumbnail images. May require restart to take effect."))
            c.set_active(config.getboolean("settings", "round"))
            self.pack_start(c, expand=False)

            vb = gtk.VBox(spacing=6)
            c = ConfigCheckButton(
                _("Search after _typing"), 'settings', 'eager_search')
            c.set_active(config.getboolean('settings', 'eager_search'))
            c.set_tooltip_text(_("Show search results after the user "
                "stops typing."))
            vb.pack_start(c)
            c = ConfigCheckButton(
                _("Color _search terms"), 'browsers', 'color')
            c.set_active(config.getboolean("browsers", "color"))
            c.set_tooltip_text(_("Display simple searches in blue, "
                     "advanced ones in green, and invalid ones in red"))
            vb.pack_start(c)
            f = qltk.Frame(_("Search Library"), child=vb)
            self.pack_start(f, expand=False)

            c1 = ConfigCheckButton(
                _("Confirm _multiple ratings"),
                'browsers', 'rating_confirm_multiple')
            c1.set_active(
                config.getboolean("browsers", "rating_confirm_multiple"))
            c1.set_tooltip_text(_("Ask for confirmation before changing the "
                     "rating of multiple songs at once"))

            c2 = ConfigCheckButton(
                _("Enable _one-click ratings"),
               'browsers', 'rating_click')
            c2.set_active(
                config.getboolean("browsers", "rating_click"))
            c2.set_tooltip_text(_("Enable rating by clicking on the rating "
                     "column in the song list"))

            vbox = gtk.VBox(spacing=6)
            vbox.pack_start(c1, expand=False)
            vbox.pack_start(c2, expand=False)

            f1 = qltk.Frame(_("Ratings"), child=vbox)
            self.pack_start(f1, expand=False)

        def _entry(self, entry, name, section="settings"):
            config.set(section, name, entry.get_text())

    class Player(gtk.VBox):
        def __init__(self):
            super(PreferencesWindow.Player, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Playback")

            if hasattr(player.device, 'PlayerPreferences'):
                player_prefs = player.device.PlayerPreferences()
                self.pack_start(player_prefs, expand=False)

            vbox = gtk.VBox(spacing=6)
            c = ConfigCheckButton(_("_Enable Replay Gain volume adjustment"),
                                    "player", "replaygain")
            c.set_active(config.getboolean("player", "replaygain"))
            c.connect('toggled', self.__toggled_gain)
            vbox.pack_start(c, expand=False)
            try:
                fallback_gain = config.getfloat("player", "fallback_gain")
            except:
                fallback_gain = 0.0
            adj = gtk.Adjustment(fallback_gain, -12.0, 12.0, 0.5, 0.5, 0.0)
            s = gtk.SpinButton(adj)
            s.set_digits(1)
            s.connect('changed', self.__changed, 'player', 'fallback_gain')
            s.set_tooltip_text(_("If no Replay Gain information is available "
                                 "for a song, scale the volume by this value"))
            l = gtk.Label(_("Fall-back gain (dB):"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(s)

            hb = gtk.HBox(spacing=6)
            hb.pack_start(l, expand=False)
            hb.pack_start(s, expand=False)
            vbox.pack_start(hb, expand=False)
            try:
                pre_amp_gain = config.getfloat("player", "pre_amp_gain")
            except:
                pre_amp_gain = 0
            adj = gtk.Adjustment(pre_amp_gain, -6, 6, 0.5, 0.5, 0.0)
            adj.connect('value-changed', self.__changed,
                        'player', 'pre_amp_gain')
            s = gtk.SpinButton(adj)
            s.set_digits(1)
            s.set_tooltip_text(_("Scale volume for all songs by this value, "
                                 "as long as the result will not clip"))
            l = gtk.Label(_("Pre-amp gain (dB):"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(s)
            hb = gtk.HBox(spacing=6)
            hb.pack_start(l, expand=False)
            hb.pack_start(s, expand=False)
            vbox.pack_start(hb, expand=False)
            f = qltk.Frame(_("Replay Gain Volume Adjustment"), child=vbox)
            self.pack_start(f)
            self.show_all()

        def __toggled_gain(self, activator):
            player.playlist.volume = player.playlist.volume

        def __changed(self, adj, section, name):
            config.set(section, name, str(adj.get_value()))
            player.playlist.volume = player.playlist.volume

    class Library(gtk.VBox):
        def __init__(self):
            super(PreferencesWindow.Library, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Library")
            hb = gtk.HBox(spacing=6)
            b = qltk.Button(_("_Select"), gtk.STOCK_OPEN)
            e = UndoEntry()
            e.set_text(util.fsdecode(config.get("settings", "scan")))
            hb.pack_start(e)
            e.set_tooltip_text(_("Songs placed in these folders (separated "
                     "by ':') will be added to your library"))
            hb.pack_start(b, expand=False)
            scandirs = util.split_scan_dirs(config.get("settings", "scan"))
            if scandirs and os.path.isdir(scandirs[-1]):
                # start with last added directory
                initial = scandirs[-1]
            else:
                initial = const.HOME
            b.connect('clicked', self.__select, e, initial)
            e.connect('changed', self.__changed, 'settings', 'scan')

            cb = ConfigCheckButton(
                _("_Refresh library on start"), "library", "refresh_on_start")
            cb.set_active(config.getboolean("library", "refresh_on_start"))
            vb3 = gtk.VBox(spacing=6)
            vb3.pack_start(hb)
            vb3.pack_start(cb)
            f = qltk.Frame(_("Scan _Directories"), child=vb3)
            f.get_label_widget().set_mnemonic_widget(e)
            self.pack_start(f, expand=False)

            vbox = gtk.VBox(spacing=6)
            hb = gtk.HBox(spacing=6)
            e = UndoEntry()
            e.set_text(config.get("editing", "split_on"))
            e.connect('changed', self.__changed, 'editing', 'split_on')
            e.set_tooltip_text(_('Separators for splitting tags'))
            l = gtk.Label(_("Split _on:"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            vbox.pack_start(hb, expand=False)

            cb = ConfigCheckButton(
                _("Enable _human title case"), 'editing', 'human_title_case')
            cb.set_active(config.getboolean("editing", 'human_title_case'))
            cb.set_tooltip_text(_("Uses common English rules for title casing, as in \"Dark Night of the Soul\""))
            vbox.pack_start(cb, expand=False)

            vb2 = gtk.VBox(spacing=0)
            cb = ConfigCheckButton(
                _("Save ratings and play _counts"), "editing", "save_to_songs")
            cb.set_active(config.getboolean("editing", "save_to_songs"))
            vb2.pack_start(cb)
            hb = gtk.HBox(spacing=3)
            lab = gtk.Label(_("_Email:"))
            entry = UndoEntry()
            entry.set_tooltip_text(_("Ratings and play counts will be set "
                                     "for this email address"))
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
        if self.is_not_unique(): return
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
        config.write(const.CONFIG)


