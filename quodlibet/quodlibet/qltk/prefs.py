# -*- coding: utf-8 -*-
# Copyright 2004-2012 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import gtk
import pango

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
from quodlibet.qltk.views import RCMHintedTreeView

def get_init_select_dir():
    scandirs = util.split_scan_dirs(config.get("settings", "scan"))
    if scandirs and os.path.isdir(scandirs[-1]):
        # start with last added directory
        return scandirs[-1]
    else:
        return const.HOME

class ScanBox(gtk.HBox):
    def __init__(self):
        super(ScanBox, self).__init__(spacing=6)

        self.model = model = gtk.ListStore(str)
        view = RCMHintedTreeView(model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)

        view.set_tooltip_text(_("Songs in the listed folders will be "
            "added to the library during a library refresh"))

        menu = gtk.Menu()
        remove_item = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        menu.append(remove_item)
        menu.show_all()
        view.connect('popup-menu', self.__popup, menu)
        remove_item.connect_object('activate', self.__remove, view)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_size_request(-1, max(sw.size_request()[1], 100))

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)

        def cdf(column, cell, model, iter):
            row = model[iter]
            cell.set_property('text', util.unexpand(row[0]))

        column = gtk.TreeViewColumn(None, render)
        column.set_cell_data_func(render, cdf)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        view.append_column(column)

        add = gtk.Button(stock=gtk.STOCK_ADD)
        add.connect("clicked", self.__add)
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)

        selection = view.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect("changed", self.__select_changed, remove)
        selection.emit("changed")

        remove.connect_object("clicked", self.__remove, view)

        vbox = gtk.VBox(spacing=6)
        vbox.pack_start(add, expand=False)
        vbox.pack_start(remove, expand=False)

        self.pack_start(sw)
        self.pack_start(vbox, expand=False)
        self.show_all()

        paths = util.split_scan_dirs(config.get("settings", "scan"))
        paths = map(util.fsdecode, paths)
        for path in paths:
            model.append(row=[path])

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __select_changed(self, selection, remove_button):
        remove_button.set_sensitive(selection.count_selected_rows())

    def __save(self):
        paths = map(util.fsencode, [r[0] for r in self.model])
        config.set("settings", "scan", ":".join(paths))

    def __remove(self, view):
        view.remove_selection()
        self.__save()

    def __add(self, *args):
        initial = get_init_select_dir()
        chooser = FolderChooser(self, _("Select Directories"), initial)
        fns = chooser.run()
        chooser.destroy()
        for fn in fns:
            self.model.append(row=[fn])
        self.__save()

class PreferencesWindow(qltk.UniqueWindow):
    class SongList(gtk.VBox):
        name = "songlist"
        def __init__(self):
            super(PreferencesWindow.SongList, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Song List")

            # Behaviour
            vbox = gtk.VBox(spacing=6)
            c = ConfigCheckButton(_("_Jump to playing song automatically"),
                                  'settings', 'jump', populate=True)
            c.set_tooltip_text(_("When the playing song changes, "
                                 "scroll to it in the song list"))
            vbox.pack_start(c, expand=False)
            frame = qltk.Frame(_("Behavior"), child=vbox)
            self.pack_start(frame, expand=False)

            # Columns
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
        name = "browser"
        def __init__(self):
            super(PreferencesWindow.Browsers, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Browsers")

            # Search
            vb = gtk.VBox(spacing=6)
            hb = gtk.HBox(spacing=6)
            l = gtk.Label(_("_Global filter:"))
            l.set_use_underline(True)
            e = ValidatingEntry(Query.is_valid_color)
            e.set_text(config.get("browsers", "background"))
            e.connect('changed', self._entry, 'background', 'browsers')
            e.set_tooltip_text(_("Apply this query in addition to all others"))
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            vb.pack_start(hb, expand=False)

            c = ConfigCheckButton(_("Search after _typing"),
                                  'settings', 'eager_search', populate=True)
            c.set_tooltip_text(_("Show search results after the user "
                "stops typing."))
            vb.pack_start(c, expand=False)
            # Translators: The heading of the preference group, no action
            f = qltk.Frame(Q_("heading|Search"), child=vb)
            self.pack_start(f, expand=False)

            # Ratings
            vb = gtk.VBox(spacing=6)
            c1 = ConfigCheckButton(
                    _("Confirm _multiple ratings"),
                    'browsers', 'rating_confirm_multiple', populate=True)
            c1.set_tooltip_text(_("Ask for confirmation before changing the "
                                  "rating of multiple songs at once"))

            c2 = ConfigCheckButton(_("Enable _one-click ratings"),
                                   'browsers', 'rating_click', populate=True)
            c2.set_tooltip_text(_("Enable rating by clicking on the rating "
                                  "column in the song list"))

            vbox = gtk.VBox(spacing=6)
            vbox.pack_start(c1, expand=False)
            vbox.pack_start(c2, expand=False)
            f = qltk.Frame(_("Ratings"), child=vbox)
            self.pack_start(f, expand=False)

            # Album Art
            vb = gtk.VBox(spacing=6)
            c = ConfigCheckButton(_("_Use rounded corners on thumbnails"),
                                  'albumart', 'round', populate=True)
            c.set_tooltip_text(_("Round the corners of album artwork "
                    "thumbnail images. May require restart to take effect."))
            vb.pack_start(c, expand=False)

            # Filename choice algorithm config
            cb = ConfigCheckButton(_("Prefer _embedded art"),
                                   'albumart', 'prefer_embedded', populate=True)
            cb.set_tooltip_text(_("Choose to use artwork embedded in the audio "
                                  "(where available) over other sources"))
            vb.pack_start(cb, expand=False)

            hb = gtk.HBox(spacing=3)
            cb = ConfigCheckButton(_("_Force image filename:"),
                                   'albumart', 'force_filename', populate=True)
            hb.pack_start(cb, expand=False)

            entry = UndoEntry()
            entry.set_tooltip_text(
                    _("The album art image file to use when forced"))
            entry.set_text(config.get("albumart", "filename"))
            entry.connect('changed', self.__changed_text, 'filename')
            # Disable entry when not forcing
            entry.set_sensitive(cb.get_active())
            cb.connect('toggled', self.__toggled_force_filename, entry)
            hb.pack_start(entry)
            vb.pack_start(hb, expand=False)

            f = qltk.Frame(_("Album Art"), child=vb)
            self.pack_start(f, expand=False)

        def __changed_text(self, entry, name):
            config.set('albumart', name, entry.get_text())

        def __toggled_force_filename(self, cb, fn_entry):
            fn_entry.set_sensitive(cb.get_active())

        def _entry(self, entry, name, section="settings"):
            config.set(section, name, entry.get_text())

    class Player(gtk.VBox):
        name = "playback"
        def __init__(self):
            super(PreferencesWindow.Player, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Playback")

            # player backend
            if player.backend and hasattr(player.device, 'PlayerPreferences'):
                player_prefs = player.device.PlayerPreferences()
                f = qltk.Frame(_("Output Configuration"), child=player_prefs)
                self.pack_start(f, expand=False)

            # replaygain
            fallback_gain = config.getfloat("player", "fallback_gain", 0.0)
            adj = gtk.Adjustment(fallback_gain, -12.0, 12.0, 0.5, 0.5, 0.0)
            fb_spin = gtk.SpinButton(adj)
            fb_spin.set_digits(1)
            fb_spin.connect('changed', self.__changed,
                            'player', 'fallback_gain')
            fb_spin.set_tooltip_text(
                _("If no Replay Gain information is available "
                  "for a song, scale the volume by this value"))

            fb_label = gtk.Label(_("_Fall-back gain (dB):"))
            fb_label.set_use_underline(True)
            fb_label.set_mnemonic_widget(fb_spin)

            pre_amp_gain = config.getfloat("player", "pre_amp_gain", 0.0)
            adj = gtk.Adjustment(pre_amp_gain, -6, 6, 0.5, 0.5, 0.0)
            adj.connect('value-changed', self.__changed,
                        'player', 'pre_amp_gain')
            pre_spin = gtk.SpinButton(adj)
            pre_spin.set_digits(1)
            pre_spin.set_tooltip_text(
                _("Scale volume for all songs by this value, "
                  "as long as the result will not clip"))

            pre_label = gtk.Label(_("_Pre-amp gain (dB):"))
            pre_label.set_use_underline(True)
            pre_label.set_mnemonic_widget(pre_spin)

            widgets = [pre_label, pre_spin, fb_label, fb_spin]
            c = ConfigCheckButton(_("_Enable Replay Gain volume adjustment"),
                                    "player", "replaygain", populate=True)
            c.connect('toggled', self.__toggled_gain, widgets)

            # packing
            table = gtk.Table(3, 2)
            table.set_col_spacings(6)
            table.set_row_spacings(6)

            table.attach(c, 0, 2, 0, 1)
            fb_label.set_alignment(0, 0.5)
            table.attach(fb_label, 0, 1, 1, 2,
                         xoptions=0)
            pre_label.set_alignment(0, 0.5)
            table.attach(pre_label, 0, 1, 2, 3,
                         xoptions=0)

            fb_align = gtk.Alignment(0, 0.5, 0, 1)
            fb_align.add(fb_spin)
            table.attach(fb_align, 1, 2, 1, 2)

            pre_align = gtk.Alignment(0, 0.5, 0, 1)
            pre_align.add(pre_spin)
            table.attach(pre_align, 1, 2, 2, 3)

            f = qltk.Frame(_("Replay Gain Volume Adjustment"), child=table)

            c.emit('toggled')

            self.pack_start(f, expand=False)
            self.show_all()

        def __toggled_gain(self, activator, widgets):
            if player.playlist: # tests
                player.playlist.volume = player.playlist.volume
            for widget in widgets:
                widget.set_sensitive(activator.get_active())

        def __changed(self, adj, section, name):
            config.set(section, name, str(adj.get_value()))
            player.playlist.volume = player.playlist.volume

    class Tagging(gtk.VBox):
        name = "tagging"
        def __init__(self):
            super(PreferencesWindow.Tagging, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Tags")

            vbox = gtk.VBox(spacing=6)

            cb = ConfigCheckButton(_("Auto-save tag changes"),
                                   'editing', 'auto_save_changes',
                                   populate=True)
            cb.set_tooltip_text(_("Save changes to tags without confirmation "
                                  "when editing multiple files"))
            vbox.pack_start(cb, expand=False)

            cb = ConfigCheckButton(_("Show _programmatic tags"),
                                   'editing', 'alltags', populate=True)
            cb.set_tooltip_text(
                    _("Access all tags, including machine-generated ones "
                      "e.g. MusicBrainz or Replay Gain tags"))
            vbox.pack_start(cb, expand=False)

            hb = gtk.HBox(spacing=6)
            e = UndoEntry()
            e.set_text(config.get("editing", "split_on"))
            e.connect('changed', self.__changed, 'editing', 'split_on')
            e.set_tooltip_text(
                    _("A list of separators to use when splitting tag values. "
                      "The list is space-separated"))
            l = gtk.Label(_("Split _on:"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(e)
            hb.pack_start(l, expand=False)
            hb.pack_start(e)
            vbox.pack_start(hb, expand=False)

            vb2 = gtk.VBox(spacing=6)
            cb = ConfigCheckButton(_("Save ratings and play _counts"),
                                   "editing", "save_to_songs", populate=True)
            vb2.pack_start(cb)
            hb = gtk.HBox(spacing=6)
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

            f = qltk.Frame(_("Tag Editing"), child=vbox)
            self.pack_start(f, expand=False)

            f = qltk.Frame(_("Ratings"), child=vb2)
            self.pack_start(f, expand=False)

            self.show_all()

        def __changed(self, entry, section, name):
            config.set(section, name, entry.get_text())

    class Library(gtk.VBox):
        name = "library"
        def __init__(self):
            super(PreferencesWindow.Library, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Library")

            cb = ConfigCheckButton(_("_Refresh library on start"),
                                   "library", "refresh_on_start", populate=True)
            scan_dirs = ScanBox()

            vb3 = gtk.VBox(spacing=6)
            vb3.pack_start(scan_dirs)

            def refresh_cb(button):
                from quodlibet.library import library
                from quodlibet.util import copool
                paths = util.split_scan_dirs(config.get("settings", "scan"))
                exclude = config.get("library", "exclude").split(":")
                copool.add(library.rebuild,
                   paths, False, exclude, cofuncid="library", funcid="library")

            refresh = qltk.Button(_("Refresh Library"), gtk.STOCK_REFRESH)
            refresh.connect("clicked", refresh_cb)

            hb = gtk.HBox(spacing=6)
            hb.pack_start(cb)
            hb.pack_start(refresh, expand=False)

            vb3.pack_start(hb, expand=False)
            f = qltk.Frame(_("Scan Directories"), child=vb3)
            self.pack_start(f, expand=False)

            self.show_all()

    def __init__(self, parent):
        if self.is_not_unique(): return
        super(PreferencesWindow, self).__init__()
        self.set_title(_("Preferences") + " - Quod Libet")
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(qltk.get_top_parent(parent))

        self.__notebook = notebook = qltk.Notebook()
        for Page in [self.SongList, self.Browsers, self.Player,
            self.Library, self.Tagging]: notebook.append_page(Page())

        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect_object('clicked', lambda x: x.destroy(), self)
        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        button_box.pack_start(close)

        vbox = gtk.VBox(spacing=12)
        vbox.pack_start(notebook)
        vbox.pack_start(button_box, expand=False)
        self.add(vbox)

        self.connect_object('destroy', PreferencesWindow.__destroy, self)
        self.show_all()

    def set_page(self, name):
        notebook = self.__notebook
        for p in range(notebook.get_n_pages()):
            if notebook.get_nth_page(p).name == name:
                notebook.set_current_page(p)

    def __destroy(self):
        config.write(const.CONFIG)


