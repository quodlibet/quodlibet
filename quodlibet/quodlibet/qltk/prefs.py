# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Steven Robertson
#           2011-2017 Nick Boultbee
#           2013      Christoph Reiter
#           2014      Jan Path
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import config
from quodlibet import qltk
from quodlibet import util
from quodlibet import app
from quodlibet import C_, _
from quodlibet.config import RATINGS, DurationFormat, DURATION

from quodlibet.qltk.ccb import ConfigCheckButton as CCB
from quodlibet.qltk.data_editors import TagListEditor
from quodlibet.qltk.entry import ValidatingEntry, UndoEntry
from quodlibet.query._query import Query
from quodlibet.qltk.scanbox import ScanBox
from quodlibet.qltk.maskedbox import MaskedBox
from quodlibet.qltk.songlist import SongList, get_columns
from quodlibet.qltk.window import UniqueWindow
from quodlibet.qltk.x import Button, Align
from quodlibet.qltk import Icons
from quodlibet.util import copool, format_time_preferred
from quodlibet.util.dprint import print_d
from quodlibet.util.library import emit_signal, get_scan_dirs, scan_library
from quodlibet.util import connect_obj


class PreferencesWindow(UniqueWindow):
    """The tabbed container window for the main preferences GUI.
    Individual tabs are encapsulated as inner classes inheriting from `VBox`"""

    class SongList(Gtk.VBox):
        name = "songlist"

        PREDEFINED_TAGS = [
            ("~#disc", _("_Disc")),
            ("~#track", _("_Track")),
            ("grouping", _("Grou_ping")),

            ("artist", _("_Artist")),
            ("album", _("Al_bum")),
            ("title", util.tag("title")),

            ("genre", _("_Genre")),
            ("date", _("_Date")),
            ("~basename", _("_Filename")),

            ("~#length", _("_Length")),
            ("~rating", _("_Rating")),
            ("~#filesize", util.tag("~#filesize"))]

        def __init__(self):
            def create_behaviour_frame():
                vbox = Gtk.VBox(spacing=6)
                c = CCB(_("_Jump to playing song automatically"),
                        'settings', 'jump', populate=True,
                        tooltip=_("When the playing song changes, "
                                  "scroll to it in the song list"))
                vbox.pack_start(c, False, True, 0)
                return qltk.Frame(_("Behavior"), child=vbox)

            def create_visible_columns_frame():
                buttons = {}
                vbox = Gtk.VBox(spacing=12)
                table = Gtk.Table.new(3, 3, True)
                for i, (k, t) in enumerate(self.PREDEFINED_TAGS):
                    x, y = i % 3, i / 3
                    buttons[k] = Gtk.CheckButton(label=t, use_underline=True)
                    table.attach(buttons[k], x, x + 1, y, y + 1)
                vbox.pack_start(table, False, True, 0)
                # Other columns
                hbox = Gtk.HBox(spacing=6)
                l = Gtk.Label(label=_("_Others:"), use_underline=True)
                hbox.pack_start(l, False, True, 0)
                self.others = others = UndoEntry()
                others.set_sensitive(False)
                # Stock edit doesn't have ellipsis chars.
                edit_button = Gtk.Button(
                    label=_(u"_Edit…"), use_underline=True)
                edit_button.connect("clicked", self.__config_cols, buttons)
                edit_button.set_tooltip_text(
                    _("Add or remove additional column "
                      "headers"))
                l.set_mnemonic_widget(edit_button)
                l.set_use_underline(True)
                hbox.pack_start(others, True, True, 0)
                vbox.pack_start(hbox, False, True, 0)
                b = Gtk.HButtonBox()
                b.set_layout(Gtk.ButtonBoxStyle.END)
                b.pack_start(edit_button, True, True, 0)
                vbox.pack_start(b, True, True, 0)
                return qltk.Frame(_("Visible Columns"), child=vbox), buttons

            def create_columns_prefs_frame():
                tiv = Gtk.CheckButton(label=_("Title includes _version"),
                                      use_underline=True)
                aio = Gtk.CheckButton(label=_("Artist includes all _people"),
                                      use_underline=True)
                aip = Gtk.CheckButton(label=_("Album includes _disc subtitle"),
                                      use_underline=True)
                fip = Gtk.CheckButton(label=_("Filename includes _folder"),
                                      use_underline=True)
                self._toggle_data = [
                    (tiv, "title", "~title~version"),
                    (aip, "album", "~album~discsubtitle"),
                    (fip, "~basename", "~filename"),
                    (aio, "artist", "~people")
                ]
                t = Gtk.Table.new(2, 2, True)
                t.attach(tiv, 0, 1, 0, 1)
                t.attach(aip, 0, 1, 1, 2)
                t.attach(aio, 1, 2, 0, 1)
                t.attach(fip, 1, 2, 1, 2)
                return qltk.Frame(_("Column Preferences"), child=t)

            def create_apply_button():
                vbox = Gtk.VBox(spacing=12)
                apply = Button(_("_Apply"))
                apply.set_tooltip_text(
                    _("Apply current configuration to song list, "
                      "adding new columns to the end"))
                apply.connect('clicked', self.__apply, buttons)
                # Apply on destroy, else config gets mangled
                self.connect('destroy', self.__apply, buttons)
                b = Gtk.HButtonBox()
                b.set_layout(Gtk.ButtonBoxStyle.END)
                b.pack_start(apply, True, True, 0)
                vbox.pack_start(b, True, True, 0)
                return vbox

            super(PreferencesWindow.SongList, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Song List")
            self.pack_start(create_behaviour_frame(), False, True, 0)
            columns_frame, buttons = create_visible_columns_frame()
            self.pack_start(columns_frame, False, True, 0)
            self.pack_start(create_columns_prefs_frame(), False, True, 0)
            self.pack_start(create_apply_button(), True, True, 0)
            self.__update(buttons, self._toggle_data, get_columns())

            for child in self.get_children():
                child.show_all()

        def __update(self, buttons, toggle_data, columns):
            """Updates all widgets based on the passed column list"""

            columns = list(columns)

            for key, widget in buttons.items():
                widget.set_active(key in columns)
                if key in columns:
                    columns.remove(key)

            for (check, off, on) in toggle_data:
                if on in columns:
                    buttons[off].set_active(True)
                    check.set_active(True)
                    columns.remove(on)

            self.others.set_text(", ".join(columns))
            self.other_cols = columns

        def __get_current_columns(self, buttons):
            """Given the current column list and the widgets states compute
            a new column list.
            """

            new_headers = set()
            # Get the checked headers
            for key, name in self.PREDEFINED_TAGS:
                if buttons[key].get_active():
                    new_headers.add(key)
                # And the customs
            new_headers.update(set(self.other_cols))

            on_to_off = dict((on, off) for (w, off, on) in self._toggle_data)
            result = []
            cur_cols = get_columns()
            for h in cur_cols:
                if h in new_headers:
                    result.append(h)
                else:
                    try:
                        alternative = on_to_off[h]
                        if alternative in new_headers:
                            result.append(alternative)
                    except KeyError:
                        pass

            # Add new ones on the end
            result.extend(new_headers - set(result))

            # After this, do the substitutions
            for (check, off, on) in self._toggle_data:
                if check.get_active():
                    try:
                        result[result.index(off)] = on
                    except ValueError:
                        pass

            return result

        def __apply(self, button, buttons):
            result = self.__get_current_columns(buttons)
            SongList.set_all_column_headers(result)

        def __config_cols(self, button, buttons):
            def __closed(widget):
                cols = widget.get_strings()
                self.__update(buttons, self._toggle_data, cols)

            columns = self.__get_current_columns(buttons)
            m = TagListEditor(_("Edit Columns"), columns)
            m.set_transient_for(qltk.get_top_parent(self))
            m.connect('destroy', __closed)
            m.show()

    class Browsers(Gtk.VBox):
        name = "browser"

        def __init__(self):
            def create_display_frame():
                vbox = Gtk.VBox(spacing=6)
                model = Gtk.ListStore(str, str)

                def on_changed(combo):
                    it = combo.get_active_iter()
                    if it is None:
                        return
                    DURATION.format = model[it][0]
                    app.window.songlist.info.refresh()
                    app.window.qexpander.refresh()
                    # TODO: refresh info windows ideally too (but see #2019)

                def draw_duration(column, cell, model, it, data):
                    df, example = model[it]
                    cell.set_property('text', example)

                for df in sorted(DurationFormat.values):
                    # 4954s == longest ever CD, FWIW
                    model.append([df, format_time_preferred(4954, df)])
                duration = Gtk.ComboBox(model=model)
                cell = Gtk.CellRendererText()
                duration.pack_start(cell, True)
                duration.set_cell_data_func(cell, draw_duration, None)
                index = sorted(DurationFormat.values).index(DURATION.format)
                duration.set_active(index)
                duration.connect('changed', on_changed)
                hbox = Gtk.HBox(spacing=6)
                label = Gtk.Label(label=_("Duration totals") + ":",
                                  use_underline=True)
                label.set_mnemonic_widget(duration)
                hbox.pack_start(label, False, True, 0)
                hbox.pack_start(duration, False, True, 0)

                vbox.pack_start(hbox, False, True, 0)
                return qltk.Frame(_("Display"), child=vbox)

            def create_search_frame():
                vb = Gtk.VBox(spacing=6)
                hb = Gtk.HBox(spacing=6)
                l = Gtk.Label(label=_("_Global filter:"))
                l.set_use_underline(True)
                e = ValidatingEntry(Query.validator)
                e.set_text(config.get("browsers", "background"))
                e.connect('changed', self._entry, 'background', 'browsers')
                e.set_tooltip_text(
                    _("Apply this query in addition to all others"))
                l.set_mnemonic_widget(e)
                hb.pack_start(l, False, True, 0)
                hb.pack_start(e, True, True, 0)
                vb.pack_start(hb, False, True, 0)
                # Translators: The heading of the preference group, no action
                return qltk.Frame(C_("heading", "Search"), child=vb)

            super(PreferencesWindow.Browsers, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Browsers")
            self.pack_start(create_search_frame(), False, True, 0)
            self.pack_start(create_display_frame(), False, True, 0)

            # Ratings
            vb = Gtk.VBox(spacing=6)
            c1 = CCB(_("Confirm _multiple ratings"),
                     'browsers', 'rating_confirm_multiple', populate=True,
                     tooltip=_("Ask for confirmation before changing the "
                               "rating of multiple songs at once"))

            c2 = CCB(_("Enable _one-click ratings"),
                     'browsers', 'rating_click', populate=True,
                     tooltip=_("Enable rating by clicking on the rating "
                               "column in the song list"))

            vbox = Gtk.VBox(spacing=6)
            vbox.pack_start(c1, False, True, 0)
            vbox.pack_start(c2, False, True, 0)
            f = qltk.Frame(_("Ratings"), child=vbox)
            self.pack_start(f, False, True, 0)

            vb = Gtk.VBox(spacing=6)

            # Filename choice algorithm config
            cb = CCB(_("Prefer _embedded art"),
                     'albumart', 'prefer_embedded', populate=True,
                     tooltip=_("Choose to use artwork embedded in the audio "
                               "(where available) over other sources"))
            vb.pack_start(cb, False, True, 0)

            hb = Gtk.HBox(spacing=3)
            cb = CCB(_("_Fixed image filename:"),
                     'albumart', 'force_filename', populate=True,
                     tooltip=_("The single image filename to use if "
                               "selected"))
            hb.pack_start(cb, False, True, 0)

            entry = UndoEntry()
            entry.set_tooltip_text(
                    _("The album art image file to use when forced"
                      " (supports wildcards)"))
            entry.set_text(config.get("albumart", "filename"))
            entry.connect('changed', self.__changed_text, 'filename')
            # Disable entry when not forcing
            entry.set_sensitive(cb.get_active())
            cb.connect('toggled', self.__toggled_force_filename, entry)
            hb.pack_start(entry, True, True, 0)
            vb.pack_start(hb, False, True, 0)

            f = qltk.Frame(_("Album Art"), child=vb)
            self.pack_start(f, False, True, 0)

            for child in self.get_children():
                child.show_all()

        def __changed_text(self, entry, name):
            config.set('albumart', name, entry.get_text())

        def __toggled_force_filename(self, cb, fn_entry):
            fn_entry.set_sensitive(cb.get_active())

        def _entry(self, entry, name, section="settings"):
            config.set(section, name, entry.get_text())

    class Player(Gtk.VBox):
        name = "playback"

        def __init__(self):
            super(PreferencesWindow.Player, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Playback")

            # player backend
            if app.player and hasattr(app.player, 'PlayerPreferences'):
                player_prefs = app.player.PlayerPreferences()
                f = qltk.Frame(_("Output Configuration"), child=player_prefs)
                self.pack_start(f, False, True, 0)

            # replaygain
            fallback_gain = config.getfloat("player", "fallback_gain", 0.0)
            adj = Gtk.Adjustment.new(fallback_gain, -12.0, 12.0, 0.5, 0.5, 0.0)
            fb_spin = Gtk.SpinButton(adjustment=adj)
            fb_spin.set_digits(1)
            fb_spin.connect('changed', self.__changed,
                            'player', 'fallback_gain')
            fb_spin.set_tooltip_text(
                _("If no Replay Gain information is available "
                  "for a song, scale the volume by this value"))

            fb_label = Gtk.Label(label=_("_Fall-back gain (dB):"))
            fb_label.set_use_underline(True)
            fb_label.set_mnemonic_widget(fb_spin)

            pre_amp_gain = config.getfloat("player", "pre_amp_gain", 0.0)
            adj = Gtk.Adjustment.new(pre_amp_gain, -12, 12, 0.5, 0.5, 0.0)
            adj.connect('value-changed', self.__changed,
                        'player', 'pre_amp_gain')
            pre_spin = Gtk.SpinButton(adjustment=adj)
            pre_spin.set_digits(1)
            pre_spin.set_tooltip_text(
                _("Scale volume for all songs by this value, "
                  "as long as the result will not clip"))

            pre_label = Gtk.Label(label=_("_Pre-amp gain (dB):"))
            pre_label.set_use_underline(True)
            pre_label.set_mnemonic_widget(pre_spin)

            widgets = [pre_label, pre_spin, fb_label, fb_spin]
            c = CCB(_("_Enable Replay Gain volume adjustment"),
                    "player", "replaygain", populate=True)
            c.connect('toggled', self.__toggled_gain, widgets)

            # packing
            table = Gtk.Table.new(3, 2, False)
            table.set_col_spacings(6)
            table.set_row_spacings(6)

            table.attach(c, 0, 2, 0, 1)
            fb_label.set_alignment(0, 0.5)
            table.attach(fb_label, 0, 1, 1, 2,
                         xoptions=Gtk.AttachOptions.FILL)
            pre_label.set_alignment(0, 0.5)
            table.attach(pre_label, 0, 1, 2, 3,
                         xoptions=Gtk.AttachOptions.FILL)

            fb_align = Align(halign=Gtk.Align.START)
            fb_align.add(fb_spin)
            table.attach(fb_align, 1, 2, 1, 2)

            pre_align = Align(halign=Gtk.Align.START)
            pre_align.add(pre_spin)
            table.attach(pre_align, 1, 2, 2, 3)

            f = qltk.Frame(_("Replay Gain Volume Adjustment"), child=table)

            c.emit('toggled')

            self.pack_start(f, False, True, 0)

            vbox = Gtk.VBox()
            c = CCB(_("_Continue playback on startup"),
                    "player", "restore_playing", populate=True,
                    tooltip=_("If music is playing on shutdown, automatically "
                              "start playing on next startup"))
            vbox.pack_start(c, False, False, 0)

            f = qltk.Frame(_("Startup"), child=vbox)
            self.pack_start(f, False, True, 0)

            for child in self.get_children():
                child.show_all()

        def __toggled_gain(self, activator, widgets):
            if app.player:
                # tests
                app.player.reset_replaygain()
            for widget in widgets:
                widget.set_sensitive(activator.get_active())

        def __changed(self, adj, section, name):
            config.set(section, name, str(adj.get_value()))
            app.player.reset_replaygain()

    class Tagging(Gtk.VBox):
        name = "tagging"

        def ratings_vbox(self):
            """Returns a new VBox containing all ratings widgets"""
            vb = Gtk.VBox(spacing=6)

            # Default Rating
            model = Gtk.ListStore(float)
            default_combo = Gtk.ComboBox(model=model)
            default_lab = Gtk.Label(label=_("_Default rating:"))
            default_lab.set_use_underline(True)
            default_lab.set_alignment(0, 0.5)

            def draw_rating(column, cell, model, it, data):
                num = model[it][0]
                text = "%0.2f: %s" % (num, util.format_rating(num))
                cell.set_property('text', text)

            def default_rating_changed(combo, model):
                it = combo.get_active_iter()
                if it is None:
                    return
                RATINGS.default = model[it][0]
                qltk.redraw_all_toplevels()

            def populate_default_rating_model(combo, num):
                model = combo.get_model()
                model.clear()
                deltas = []
                default = RATINGS.default
                precision = RATINGS.precision
                for i in range(0, num + 1):
                    r = i * precision
                    model.append(row=[r])
                    deltas.append((abs(default - r), i))
                active = sorted(deltas)[0][1]
                print_d("Choosing #%d (%.2f), closest to current %.2f"
                        % (active, precision * active, default))
                combo.set_active(active)

            cell = Gtk.CellRendererText()
            default_combo.pack_start(cell, True)
            default_combo.set_cell_data_func(cell, draw_rating, None)
            default_combo.connect('changed', default_rating_changed, model)
            default_lab.set_mnemonic_widget(default_combo)

            def refresh_default_combo(num):
                populate_default_rating_model(default_combo, num)

            # Rating Scale
            model = Gtk.ListStore(int)
            scale_combo = Gtk.ComboBox(model=model)
            scale_lab = Gtk.Label(label=_("Rating _scale:"))
            scale_lab.set_use_underline(True)
            scale_lab.set_mnemonic_widget(scale_combo)

            cell = Gtk.CellRendererText()
            scale_combo.pack_start(cell, False)
            num = RATINGS.number
            for i in [1, 2, 3, 4, 5, 6, 8, 10]:
                it = model.append(row=[i])
                if i == num:
                    scale_combo.set_active_iter(it)

            def draw_rating_scale(column, cell, model, it, data):
                num_stars = model[it][0]
                text = "%d: %s" % (num_stars, RATINGS.full_symbol * num_stars)
                cell.set_property('text', text)

            def rating_scale_changed(combo, model):
                it = combo.get_active_iter()
                if it is None:
                    return
                RATINGS.number = num = model[it][0]
                refresh_default_combo(num)

            refresh_default_combo(RATINGS.number)
            scale_combo.set_cell_data_func(cell, draw_rating_scale, None)
            scale_combo.connect('changed', rating_scale_changed, model)

            default_align = Align(halign=Gtk.Align.START)
            default_align.add(default_lab)
            scale_align = Align(halign=Gtk.Align.START)
            scale_align.add(scale_lab)

            grid = Gtk.Grid(column_spacing=6, row_spacing=6)
            grid.add(scale_align)
            grid.add(scale_combo)
            grid.attach(default_align, 0, 1, 1, 1)
            grid.attach(default_combo, 1, 1, 1, 1)
            vb.pack_start(grid, False, False, 6)

            # Bayesian Factor
            bayesian_factor = config.getfloat("settings",
                                              "bayesian_rating_factor", 0.0)
            adj = Gtk.Adjustment.new(bayesian_factor, 0.0, 10.0, 0.5, 0.5, 0.0)
            bayes_spin = Gtk.SpinButton(adjustment=adj, numeric=True)
            bayes_spin.set_digits(1)
            bayes_spin.connect('changed', self.__changed_and_signal_library,
                               'settings', 'bayesian_rating_factor')
            bayes_spin.set_tooltip_text(
                _("Bayesian Average factor (C) for aggregated ratings.\n"
                  "0 means a conventional average, higher values mean that "
                  "albums with few tracks will have less extreme ratings. "
                  "Changing this value triggers a re-calculation for all "
                  "albums."))
            bayes_label = Gtk.Label(label=_("_Bayesian averaging amount:"))
            bayes_label.set_use_underline(True)
            bayes_label.set_mnemonic_widget(bayes_spin)

            # Save Ratings
            hb = Gtk.HBox(spacing=6)
            hb.pack_start(bayes_label, False, True, 0)
            hb.pack_start(bayes_spin, False, True, 0)
            vb.pack_start(hb, True, True, 0)
            cb = CCB(_("Save ratings and play _counts in tags"),
                     "editing", "save_to_songs", populate=True)

            def update_entry(widget, email_entry):
                email_entry.set_sensitive(widget.get_active())

            vb.pack_start(cb, True, True, 0)
            hb = Gtk.HBox(spacing=6)
            lab = Gtk.Label(label=_("_Email:"))
            entry = UndoEntry()
            entry.set_tooltip_text(_("Ratings and play counts will be saved "
                                     "in tags for this email address"))
            entry.set_text(config.get("editing", "save_email"))
            entry.connect('changed', self.__changed, 'editing', 'save_email')

            # Disable the entry if not saving to tags
            cb.connect('clicked', update_entry, entry)
            update_entry(cb, entry)

            hb.pack_start(lab, False, True, 0)
            hb.pack_start(entry, True, True, 0)
            lab.set_mnemonic_widget(entry)
            lab.set_use_underline(True)
            vb.pack_start(hb, True, True, 0)

            return vb

        def tag_editing_vbox(self):
            """Returns a new VBox containing all tag editing widgets"""
            vbox = Gtk.VBox(spacing=6)
            cb = CCB(_("Auto-save tag changes"), 'editing',
                     'auto_save_changes', populate=True,
                     tooltip=_("Save changes to tags without confirmation "
                               "when editing multiple files"))
            vbox.pack_start(cb, False, True, 0)
            hb = Gtk.HBox(spacing=6)
            e = UndoEntry()
            e.set_text(config.get("editing", "split_on"))
            e.connect('changed', self.__changed, 'editing', 'split_on')
            e.set_tooltip_text(
                _("A set of separators to use when splitting tag values "
                  "in the tag editor. "
                  "The list is space-separated"))

            def do_revert_split(button, section, option):
                config.reset(section, option)
                e.set_text(config.get(section, option))

            split_revert = Button(_("_Revert"), Icons.DOCUMENT_REVERT)
            split_revert.connect("clicked", do_revert_split, "editing",
                                 "split_on")
            l = Gtk.Label(label=_("Split _on:"))
            l.set_use_underline(True)
            l.set_mnemonic_widget(e)
            hb.pack_start(l, False, True, 0)
            hb.pack_start(e, True, True, 0)
            hb.pack_start(split_revert, False, True, 0)
            vbox.pack_start(hb, False, True, 0)
            return vbox

        def __init__(self):
            super(PreferencesWindow.Tagging, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Tags")
            self._songs = []

            f = qltk.Frame(_("Tag Editing"), child=(self.tag_editing_vbox()))
            self.pack_start(f, False, True, 0)

            f = qltk.Frame(_("Ratings"), child=self.ratings_vbox())
            self.pack_start(f, False, True, 0)

            for child in self.get_children():
                child.show_all()

        def __changed(self, entry, section, name):
            config.set(section, name, entry.get_text())

        def __changed_and_signal_library(self, entry, section, name):
            config.set(section, name, str(entry.get_value()))
            print_d("Signalling \"changed\" to entire library. Hold tight...")
            # Cache over clicks
            self._songs = self._songs or list(app.library.values())
            copool.add(emit_signal, self._songs, funcid="library changed",
                       name=_("Updating for new ratings"))

    class Library(Gtk.VBox):
        name = "library"

        def __init__(self):
            super(PreferencesWindow.Library, self).__init__(spacing=12)
            self.set_border_width(12)
            self.title = _("Library")

            cb = CCB(_("Scan library _on start"),
                     "library", "refresh_on_start", populate=True)
            scan_dirs = ScanBox()

            vb3 = Gtk.VBox(spacing=6)
            vb3.pack_start(scan_dirs, True, True, 0)

            def refresh_cb(button):
                scan_library(app.library, force=False)

            refresh = qltk.Button(_("_Scan Library"), Icons.VIEW_REFRESH)
            refresh.connect("clicked", refresh_cb)
            refresh.set_tooltip_text(_("Check for changes in your library"))

            def reload_cb(button):
                scan_library(app.library, force=True)

            reload_ = qltk.Button(_("Re_build Library"), Icons.VIEW_REFRESH)
            reload_.connect("clicked", reload_cb)
            reload_.set_tooltip_text(
                _("Reload all songs in your library. "
                  "This can take a long time."))

            grid = Gtk.Grid(column_spacing=6, row_spacing=6)
            cb.props.hexpand = True
            grid.attach(cb, 0, 0, 1, 1)
            grid.attach(refresh, 1, 0, 1, 1)
            grid.attach(reload_, 1, 1, 1, 1)

            vb3.pack_start(grid, False, True, 0)
            f = qltk.Frame(_("Scan Directories"), child=vb3)
            self.pack_start(f, False, True, 0)

            # during testing
            if app.library is not None:
                masked = MaskedBox(app.library)
                f = qltk.Frame(_("Hidden Songs"), child=masked)
                self.pack_start(f, False, True, 0)

            for child in self.get_children():
                child.show_all()

    def __init__(self, parent):
        if self.is_not_unique():
            return
        super(PreferencesWindow, self).__init__()
        self.current_scan_dirs = get_scan_dirs()
        self.set_title(_("Preferences"))
        self.set_resizable(False)
        self.set_transient_for(qltk.get_top_parent(parent))

        self.__notebook = notebook = qltk.Notebook()
        for Page in [self.SongList, self.Browsers, self.Player,
                     self.Library, self.Tagging]:
            page = Page()
            page.show()
            notebook.append_page(page)

        page_name = config.get("memory", "prefs_page", "")
        self.set_page(page_name)

        def on_switch_page(notebook, page, page_num):
            config.set("memory", "prefs_page", page.name)

        notebook.connect("switch-page", on_switch_page)

        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        connect_obj(close, 'clicked', lambda x: x.destroy(), self)
        button_box = Gtk.HButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.END)
        button_box.pack_start(close, True, True, 0)

        self.use_header_bar()
        if self.has_close_button():
            self.set_border_width(0)
            notebook.set_show_border(False)
            self.add(notebook)
        else:
            self.set_border_width(12)
            vbox = Gtk.VBox(spacing=12)
            vbox.pack_start(notebook, True, True, 0)
            vbox.pack_start(button_box, False, True, 0)
            self.add(vbox)

        connect_obj(self, 'destroy', PreferencesWindow.__destroy, self)

        self.get_child().show_all()

    def set_page(self, name):
        notebook = self.__notebook
        for p in range(notebook.get_n_pages()):
            if notebook.get_nth_page(p).name == name:
                notebook.set_current_page(p)

    def __destroy(self):
        config.save()
        if self.current_scan_dirs != get_scan_dirs():
            print_d("Library paths have changed, re-scanning...")
            scan_library(app.library, force=False)
