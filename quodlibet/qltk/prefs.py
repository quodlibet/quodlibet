# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Steven Robertson
#           2011-2023 Nick Boultbee
#           2013      Christoph Reiter
#           2014      Jan Path
#           2023      Jej@github
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gio

from quodlibet import config
from quodlibet import qltk
from quodlibet import util
from quodlibet import app
from quodlibet import C_, _
from quodlibet.config import RATINGS, DurationFormat, DURATION

from quodlibet.qltk.ccb import ConfigSwitch as CS
from quodlibet.qltk.data_editors import TagListEditor
from quodlibet.qltk.entry import ValidatingEntry, UndoEntry, ClearEntry
from quodlibet.query._query import Query
from quodlibet.qltk.scanbox import ScanBox
from quodlibet.qltk.maskedbox import MaskedBox
from quodlibet.qltk.songlist import SongList, get_columns
from quodlibet.qltk.window import UniqueWindow
from quodlibet.qltk.x import Button, Align
from quodlibet.qltk.advanced_prefs import AdvancedPreferencesPane
from quodlibet.qltk import Icons, add_css
from quodlibet.util import copool, format_time_preferred
from quodlibet.util.dprint import print_d
from quodlibet.util.library import emit_signal, get_scan_dirs, scan_library
from quodlibet.util import connect_obj

MARGIN = 12

TOP_MARGIN = 3


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
            ("~#filesize", util.tag("~#filesize")),
        ]

        def __init__(self):
            def create_behavior_frame():
                vbox = Gtk.VBox(spacing=12)
                jump_button = CS(
                    _("_Jump to playing song automatically"),
                    "settings",
                    "jump",
                    populate=True,
                    tooltip=_(
                        "When the playing song changes, scroll to it in the song list"
                    ),
                )
                autosort_button = CS(
                    _("_Sort songs when tags are modified"),
                    "song_list",
                    "auto_sort",
                    populate=True,
                    tooltip=_(
                        "Automatically re-sort songs in "
                        "the song list when tags are modified"
                    ),
                )
                always_sortable = CS(
                    _("Always allow sorting"),
                    "song_list",
                    "always_allow_sorting",
                    populate=True,
                    tooltip=_(
                        "Allow sorting by column headers, even for playlists etc"
                    ),
                )

                def refresh_browser(*args):
                    app.window.set_sortability()

                always_sortable.connect("notify::active", refresh_browser)
                vbox.pack_start(jump_button, False, True, 0)
                vbox.pack_start(always_sortable, False, True, 0)
                vbox.pack_start(autosort_button, False, True, 0)
                return qltk.Frame(_("Behavior"), child=vbox)

            def create_visible_columns_widgets():
                buttons = {}
                vbox = Gtk.VBox(spacing=12)
                grid = Gtk.FlowBox(column_spacing=24)
                for _i, (k, t) in enumerate(self.PREDEFINED_TAGS):
                    buttons[k] = Gtk.CheckButton(label=t, use_underline=True)
                    grid.add(buttons[k])
                vbox.pack_start(grid, False, True, 0)
                # Other columns
                hbox = Gtk.HBox(spacing=12)
                l = Gtk.Label(label=_("_Others:"), use_underline=True)
                hbox.pack_start(l, False, True, 0)
                self.others = others = UndoEntry()
                others.set_sensitive(False)
                # Stock edit doesn't have ellipsis chars.
                edit_button = Button(_("_Edit…"), Icons.EDIT)
                edit_button.connect("clicked", self.__config_cols, buttons)
                edit_button.set_tooltip_text(
                    _("Add or remove additional column headers")
                )
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
                tiv = Gtk.Switch()
                aio = Gtk.Switch()
                aip = Gtk.Switch()
                fip = Gtk.Switch()
                self._toggle_data = [
                    (tiv, "title", "~title~version"),
                    (aip, "album", "~album~discsubtitle"),
                    (fip, "~basename", "~filename"),
                    (aio, "artist", "~people"),
                ]

                def pack_with_label(vb: Gtk.Box, widget: Gtk.Widget, text: str):
                    hb = Gtk.Box(spacing=12)
                    label = Gtk.Label(label=text, use_underline=True)
                    hb.pack_start(label, False, False, 0)
                    hb.pack_end(widget, False, False, 0)
                    vb.pack_start(hb, False, False, 0)

                vb = Gtk.VBox(spacing=12)
                pack_with_label(vb, tiv, _("Title includes _version"))
                pack_with_label(vb, aip, _("Album includes _disc subtitle"))
                pack_with_label(vb, aio, _("Artist includes all _people"))
                pack_with_label(vb, fip, _("Filename includes _folder"))
                return qltk.Frame(_("Column Preferences"), child=vb)

            def create_update_columns_button():
                apply = Button(_("_Update Columns"), Icons.VIEW_REFRESH)
                apply.set_tooltip_text(
                    _(
                        "Apply current configuration to song list, "
                        "adding new columns to the end"
                    )
                )
                apply.connect("clicked", self.__apply, buttons)
                # Apply on destroy, else config gets mangled
                self.connect("destroy", self.__apply, buttons)
                b = Gtk.HButtonBox()
                b.set_layout(Gtk.ButtonBoxStyle.END)
                b.pack_start(apply, True, True, 0)
                return b

            super().__init__(spacing=12)
            # Store ordered columns
            self._columns = []
            self.set_border_width(12)
            self.title = _("Song List")
            visible_columns_frame, buttons = create_visible_columns_widgets()
            self.pack_start(create_behavior_frame(), False, True, TOP_MARGIN)
            self.pack_start(visible_columns_frame, False, True, MARGIN)
            self.pack_start(create_columns_prefs_frame(), False, True, MARGIN)
            self.pack_start(create_update_columns_button(), False, False, 0)

            # Run it now
            self.__update(buttons, self._toggle_data, get_columns())

            for child in self.get_children():
                child.show_all()

        def __update(self, buttons, toggle_data, columns):
            """Updates all widgets based on the passed column list"""
            self._columns = columns
            columns = list(columns)

            for key, widget in buttons.items():
                widget.set_active(key in columns)
                if key in columns:
                    columns.remove(key)

            for check, off, on in toggle_data:
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
            for key, _name in self.PREDEFINED_TAGS:
                if buttons[key].get_active():
                    new_headers.add(key)
                # And the customs
            new_headers.update(set(self.other_cols))

            on_to_off = {on: off for (w, off, on) in self._toggle_data}
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

            # Add new ones, trying to preserve order
            for new in new_headers - set(result):
                try:
                    idx = self._columns.index(new)
                except ValueError:
                    idx = len(self._columns)
                result.insert(idx, new)

            # After this, do the substitutions
            for check, off, on in self._toggle_data:
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
                self.__update(buttons, self._toggle_data, widget.tags)

            columns = self.__get_current_columns(buttons)
            m = TagListEditor(_("Edit Columns"), columns)
            m.set_transient_for(qltk.get_top_parent(self))
            m.connect("destroy", __closed)
            m.show()

    class Browsers(Gtk.VBox):
        name = "browser"

        def __init__(self):
            def create_display_frame():
                vbox = Gtk.VBox(spacing=MARGIN)
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
                    cell.set_property("text", example)

                for df in sorted(DurationFormat.values):
                    # 4954s == longest ever CD, FWIW
                    model.append([df, format_time_preferred(4954, df)])
                duration = Gtk.ComboBox(model=model)
                cell = Gtk.CellRendererText()
                duration.pack_start(cell, True)
                duration.set_cell_data_func(cell, draw_duration, None)
                index = sorted(DurationFormat.values).index(DURATION.format)
                duration.set_active(index)
                duration.connect("changed", on_changed)
                hbox = Gtk.HBox(spacing=MARGIN)
                label = Gtk.Label(label=_("Duration totals") + ":", use_underline=True)
                label.set_mnemonic_widget(duration)
                hbox.pack_start(label, False, True, 0)
                hbox.pack_start(duration, False, True, 0)

                vbox.pack_start(hbox, False, True, 0)
                return qltk.Frame(_("Display"), child=vbox)

            def create_search_frame():
                vb = Gtk.VBox(spacing=MARGIN)
                l = Gtk.Label(label=_("_Global filter:"))
                l.set_use_underline(True)
                e = ValidatingEntry(Query.validator)
                e.set_text(config.get("browsers", "background"))
                e.connect("changed", self._entry, "background", "browsers")
                e.set_tooltip_text(_("Apply this query in addition to all others"))
                l.set_mnemonic_widget(e)
                vb.pack_start(hbox_for(l, e), False, True, 0)
                # Translators: The heading of the preference group, no action
                return qltk.Frame(C_("heading", "Search"), child=vb)

            super().__init__(spacing=MARGIN)
            self.set_border_width(MARGIN)
            self.title = _("Browsers")
            self.pack_start(create_search_frame(), False, True, TOP_MARGIN)
            self.pack_start(create_display_frame(), False, True, MARGIN)

            # Ratings
            c1 = CS(
                _("Confirm _multiple ratings"),
                "browsers",
                "rating_confirm_multiple",
                populate=True,
                tooltip=_(
                    "Ask for confirmation before changing the "
                    "rating of multiple songs at once"
                ),
            )

            c2 = CS(
                _("Enable _one-click ratings"),
                "browsers",
                "rating_click",
                populate=True,
                tooltip=_(
                    "Enable rating by clicking on the rating column in the song list"
                ),
            )

            vbox = Gtk.VBox(spacing=MARGIN)
            vbox.pack_start(c1, False, True, 0)
            vbox.pack_start(c2, False, True, 0)
            f = qltk.Frame(_("Ratings"), child=vbox)
            self.pack_start(f, False, True, MARGIN)

            vb = Gtk.VBox(spacing=MARGIN)

            # Filename choice algorithm config
            sw = CS(
                _("Prefer _embedded art"),
                "albumart",
                "prefer_embedded",
                populate=True,
                tooltip=_(
                    "Choose to use artwork embedded in the audio "
                    "(where available) over other sources"
                ),
            )
            vb.pack_start(sw, False, True, 0)

            allowed_image_filename_tooltip = _(
                "Only allow these filenames. "
                "Separate multiple files with commas. Supports wildcards."
            )

            sw = CS(
                _("Restrict image filename(s)"),
                "albumart",
                "force_filename",
                populate=True,
                tooltip=_("Restrict album art to the specified filenames."),
            )
            vb.pack_start(sw, False, True, 0)

            entry = UndoEntry()
            entry.set_tooltip_text(allowed_image_filename_tooltip)
            entry.set_text(config.get("albumart", "filename"))
            entry.connect("changed", self.__changed_text, "filename")
            # Disable entry when not forcing
            entry.set_sensitive(sw.get_active())
            sw.connect("notify::active", self.__activated_force_filename, entry)
            self.__activated_force_filename(sw, None, entry)
            hb = Gtk.Box()
            entry.set_size_request(250, -1)
            hb.pack_start(entry, False, True, 12)
            vb.pack_start(hb, False, False, 0)

            f = qltk.Frame(_("Album Art"), child=vb)
            self.pack_start(f, False, True, MARGIN)

            for child in self.get_children():
                child.show_all()

        def __changed_text(self, entry, name):
            config.set("albumart", name, entry.get_text())

        def __activated_force_filename(self, switch, state, fn_entry):
            fn_entry.set_sensitive(switch.get_active())

        def _entry(self, entry, name, section="settings"):
            config.set(section, name, entry.get_text())

    class Player(Gtk.VBox):
        name = "playback"

        def _gain_scale_for(self, adj: Gtk.Adjustment) -> Gtk.Scale:
            def format_gain(scale, value):
                return f"{value:.0f} dB"

            scale = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, adj)
            scale.set_hexpand(True)
            scale.set_show_fill_level(True)
            scale.set_property("round-digits", 0)
            scale.set_value_pos(Gtk.PositionType.LEFT)
            scale.connect("format-value", format_gain)
            return scale

        def __init__(self):
            super().__init__(spacing=MARGIN)
            self.set_border_width(12)
            self.title = _("Playback")

            self.pack_start(self.create_behavior_frame(), False, True, TOP_MARGIN)

            # player backend
            if app.player and hasattr(app.player, "PlayerPreferences"):
                player_prefs = app.player.PlayerPreferences()
                f = qltk.Frame(_("Output Configuration"), child=player_prefs)
                self.pack_start(f, False, True, MARGIN)

            fallback_gain = config.getfloat("player", "fallback_gain", 0.0)
            adj = Gtk.Adjustment.new(fallback_gain, -12.0, 6.0, 0.5, 1, 0.0)
            adj.connect("value-changed", self.__changed, "player", "fallback_gain")
            fb_scale = self._gain_scale_for(adj)
            fb_scale.set_tooltip_text(
                _(
                    "If no Replay Gain information is available "
                    "for a song, scale the volume by this value"
                )
            )

            fb_label = Gtk.Label(label=_("_Fall-back gain:"))
            fb_label.set_use_underline(True)
            fb_label.set_alignment(0, 0.5)
            fb_label.set_mnemonic_widget(fb_scale)

            pre_amp_gain = config.getfloat("player", "pre_amp_gain", 0.0)
            adj = Gtk.Adjustment.new(pre_amp_gain, -12, 12, 0.5, 1, 0)
            adj.connect("value-changed", self.__changed, "player", "pre_amp_gain")
            pre_scale = self._gain_scale_for(adj)
            pre_scale.set_tooltip_text(
                _(
                    "Scale volume for all songs by this value, "
                    "as long as the result will not clip"
                )
            )

            pre_label = Gtk.Label(label=_("_Pre-amp gain:"))
            pre_label.set_use_underline(True)
            pre_label.set_alignment(0, 0.5)
            pre_label.set_mnemonic_widget(pre_scale)

            widgets = [pre_label, pre_scale, fb_label, fb_scale]
            enable_rg = CS(
                _("_Enable Replay Gain volume adjustment"),
                "player",
                "replaygain",
                populate=True,
            )
            enable_rg.connect("notify::active", self.__activated_gain, widgets)
            self.__activated_gain(enable_rg, None, widgets)

            # packing
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            vb.pack_start(enable_rg, False, False, 0)

            grid = Gtk.Grid(column_spacing=6, row_spacing=3)
            grid.attach(fb_label, 0, 0, 1, 1)
            grid.attach(fb_scale, 1, 0, 1, 1)
            grid.attach(pre_label, 0, 1, 1, 1)
            grid.attach(pre_scale, 1, 1, 1, 1)
            hb = Gtk.Box()
            hb.pack_start(grid, True, True, 12)
            vb.pack_start(hb, False, True, 0)
            f = qltk.Frame(_("Replay Gain Volume Adjustment"), child=vb)
            self.pack_start(f, False, True, MARGIN)

            for child in self.get_children():
                child.show_all()

        def create_behavior_frame(self):
            vbox = Gtk.VBox()
            continue_play = CS(
                _("_Continue playback on startup"),
                "player",
                "restore_playing",
                populate=True,
                tooltip=_(
                    "If music is playing on shutdown, automatically "
                    "start playing on next startup"
                ),
            )
            vbox.pack_start(continue_play, False, False, 0)
            return qltk.Frame(_("Behavior"), child=vbox)

        def __activated_gain(self, activator, state, widgets):
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
            vb = Gtk.VBox(spacing=12)

            # Default Rating
            model = Gtk.ListStore(float)
            default_combo = Gtk.ComboBox(model=model)
            default_lab = Gtk.Label(label=_("_Default rating:"))
            default_lab.set_use_underline(True)
            default_lab.set_alignment(0, 0.5)

            def draw_rating(column, cell, model, it, data):
                num = model[it][0]
                text = f"{num:0.2f}: {util.format_rating(num)}"
                cell.set_property("text", text)

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
                for i in range(num + 1):
                    r = i * precision
                    model.append(row=[r])
                    deltas.append((abs(default - r), i))
                active = sorted(deltas)[0][1]
                print_d(
                    "Choosing #%d (%.2f), closest to current %.2f"
                    % (active, precision * active, default)
                )
                combo.set_active(active)

            cell = Gtk.CellRendererText()
            default_combo.pack_start(cell, True)
            default_combo.set_cell_data_func(cell, draw_rating, None)
            default_combo.connect("changed", default_rating_changed, model)
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
                cell.set_property("text", text)

            def rating_scale_changed(combo, model):
                it = combo.get_active_iter()
                if it is None:
                    return
                RATINGS.number = num = model[it][0]
                refresh_default_combo(num)

            refresh_default_combo(RATINGS.number)
            scale_combo.set_cell_data_func(cell, draw_rating_scale, None)
            scale_combo.connect("changed", rating_scale_changed, model)

            default_align = Align(halign=Gtk.Align.START)
            default_align.add(default_lab)
            scale_align = Align(halign=Gtk.Align.START)
            scale_align.add(scale_lab)

            grid = create_grid()
            grid.add(scale_align)
            grid.add(scale_combo)
            grid.attach(default_align, 0, 1, 1, 1)
            grid.attach(default_combo, 1, 1, 1, 1)
            vb.pack_start(grid, False, False, 12)

            # Bayesian Factor
            bayesian_factor = config.getfloat("settings", "bayesian_rating_factor", 0.0)
            adj = Gtk.Adjustment.new(bayesian_factor, 0.0, 10.0, 0.5, 0.5, 0.0)
            bayes_spin = Gtk.SpinButton(adjustment=adj, numeric=True)
            bayes_spin.set_digits(1)
            bayes_spin.connect(
                "changed",
                self.__changed_and_signal_library,
                "settings",
                "bayesian_rating_factor",
            )
            bayes_spin.set_tooltip_text(
                _(
                    "Bayesian Average factor (C) for aggregated ratings.\n"
                    "0 means a conventional average, higher values mean that "
                    "albums with few tracks will have less extreme ratings. "
                    "Changing this value triggers a re-calculation for all "
                    "albums."
                )
            )
            bayes_label = Gtk.Label(label=_("_Bayesian averaging amount:"))
            bayes_label.set_use_underline(True)
            bayes_label.set_mnemonic_widget(bayes_spin)

            # Save Ratings
            vb.pack_start(hbox_for(bayes_label, bayes_spin, False), True, True, 0)
            sw = CS(
                _("Save ratings and play _counts in tags"),
                "editing",
                "save_to_songs",
                populate=True,
            )

            def update_entry(widget, state, email_entry):
                email_entry.set_sensitive(widget.get_active())

            vb.pack_start(sw, True, True, 0)
            lab = Gtk.Label(label=_("_Email:"))
            entry = UndoEntry()
            entry.set_tooltip_text(
                _(
                    "Ratings and play counts will be saved "
                    "in tags for this email address"
                )
            )
            entry.set_text(config.get("editing", "save_email"))
            entry.connect("changed", self.__changed, "editing", "save_email")

            # Disable the entry if not saving to tags
            sw.connect("notify::active", update_entry, entry)
            update_entry(sw, None, entry)

            lab.set_mnemonic_widget(entry)
            lab.set_use_underline(True)
            vb.pack_start(hbox_for(lab, entry), True, True, 0)

            return vb

        def tag_editing_vbox(self):
            """Returns a new VBox containing all tag editing widgets"""
            vbox = Gtk.VBox(spacing=12)
            sw = CS(
                _("_Auto-save tag changes"),
                "editing",
                "auto_save_changes",
                populate=True,
                tooltip=_(
                    "Save changes to tags without confirmation "
                    "when editing multiple files"
                ),
            )
            vbox.pack_start(sw, False, False, 0)

            def revert_split(entry, button, _, section, option):
                config.reset(section, option)
                entry.set_text(config.get(section, option))

            split_entry = ClearEntry()
            gicon = Gio.ThemedIcon.new_from_names(["edit-clear-symbolic", "edit-clear"])
            split_entry.set_icon_from_gicon(Gtk.EntryIconPosition.SECONDARY, gicon)
            split_entry.connect("icon-release", revert_split, "editing", "split_on")
            split_entry.set_text(config.get("editing", "split_on"))
            split_entry.connect("changed", self.__changed, "editing", "split_on")
            split_entry.set_tooltip_text(
                _(
                    "A set of separators to use when splitting tag values "
                    "in the tag editor. "
                    "The list is space-separated."
                )
            )
            split_label = Gtk.Label(label=_("Split _tag on:"))
            split_label.set_use_underline(True)
            split_label.set_mnemonic_widget(split_entry)

            vbox.pack_start(hbox_for(split_label, split_entry), False, False, 0)

            sub_entry = ClearEntry()
            sub_entry.enable_clear_button()
            sub_entry.set_text(config.get("editing", "sub_split_on"))
            sub_entry.connect("changed", self.__changed, "editing", "sub_split_on")
            sub_entry.connect("icon-release", revert_split, "editing", "sub_split_on")

            sub_entry.set_tooltip_text(
                _(
                    "A set of separators to use when extracting subtags from "
                    "tags in the tag editor. "
                    "The list is space-separated, and each entry must only "
                    "contain two characters."
                )
            )

            sub_label = Gtk.Label(label=_("Split _subtag on:"))
            sub_label.set_use_underline(True)
            sub_label.set_mnemonic_widget(split_entry)

            vbox.pack_start(hbox_for(sub_label, sub_entry), False, False, 0)
            return vbox

        def __init__(self):
            super().__init__(spacing=MARGIN)
            self.set_border_width(12)
            self.title = _("Tags")
            self._songs = []

            f = qltk.Frame(_("Tag Editing"), child=(self.tag_editing_vbox()))
            self.pack_start(f, False, True, TOP_MARGIN)

            f = qltk.Frame(_("Ratings"), child=self.ratings_vbox())
            self.pack_start(f, False, True, MARGIN)

            for child in self.get_children():
                child.show_all()

        def __changed(self, entry, section, name):
            config.set(section, name, entry.get_text())

        def __changed_and_signal_library(self, entry, section, name):
            config.set(section, name, str(entry.get_value()))
            print_d('Signalling "changed" to entire library. Hold tight...')
            # Cache over clicks
            self._songs = self._songs or list(app.library.values())
            copool.add(
                emit_signal,
                self._songs,
                funcid="library changed",
                name=_("Updating for new ratings"),
            )

    class Library(Gtk.VBox):
        name = "library"

        def __init__(self):
            super().__init__(spacing=MARGIN)
            self.set_border_width(12)
            self.title = _("Library")

            def refresh_cb(button):
                scan_library(app.library, force=False)

            refresh = qltk.Button(_("_Scan Library"), Icons.VIEW_REFRESH)
            refresh.connect("clicked", refresh_cb)
            refresh.set_tooltip_text(_("Check for changes in your library"))

            def reload_cb(button):
                scan_library(app.library, force=True)

            reload_ = qltk.Button(_("Re_build Library"), Icons.DOCUMENT_NEW)
            reload_.connect("clicked", reload_cb)
            reload_.set_tooltip_text(
                _("Reload all songs in your library. This can take a long time.")
            )

            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            hbox = Gtk.Box()
            hbox.pack_end(reload_, False, True, 0)
            hbox.pack_end(refresh, False, True, 12)
            vb.pack_start(hbox, False, True, 0)

            self.pack_start(self.create_behavior_frame(), False, False, TOP_MARGIN)
            self.pack_start(self.create_scandirs_frame(), False, True, MARGIN)

            # during testing
            if app.library is not None:
                masked = MaskedBox(app.library)
                f = qltk.Frame(_("Hidden Songs"), child=masked)
                self.pack_start(f, False, True, 12)

            for child in self.get_children():
                child.show_all()

        def create_behavior_frame(self):
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            scan_at_start_sw = CS(
                _("Scan library _on start"),
                "library",
                "refresh_on_start",
                populate=True,
            )
            req_restart = _("A restart is required for any changes to take effect")
            watch_lib_sw = CS(
                _("_Watch directories for changes"),
                "library",
                "watch",
                populate=True,
                tooltip=_(
                    "Watch library directories for external file additions, "
                    "deletions and renames."
                )
                + "\n"
                + req_restart,
            )
            vb.pack_start(watch_lib_sw, False, True, 0)
            vb.pack_start(scan_at_start_sw, False, True, 0)
            return qltk.Frame(_("Behavior"), child=vb)

        def create_scandirs_frame(self):
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            scan_dirs = ScanBox()
            vb.pack_start(scan_dirs, True, True, 0)
            return qltk.Frame(_("Scan Directories"), child=vb)

    class Advanced(Gtk.VBox):
        name = "advanced"

        def __init__(self):
            super().__init__(spacing=MARGIN)
            self.set_border_width(12)
            self.title = _("Advanced")
            scrolledwin = Gtk.ScrolledWindow()
            scrolledwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolledwin.add_with_viewport(AdvancedPreferencesPane())
            self.pack_start(scrolledwin, True, True, 3)

    def __init__(self, parent, open_page=None, all_pages=True):
        if self.is_not_unique():
            return
        super().__init__()
        self.current_scan_dirs = get_scan_dirs()
        self.set_title(_("Preferences"))
        self.set_resizable(True)
        self.set_transient_for(qltk.get_top_parent(parent))

        self.__notebook = notebook = qltk.Notebook()
        pages = [self.Tagging]
        if all_pages:
            pages = (
                [self.SongList, self.Browsers, self.Player, self.Library]
                + pages
                + [self.Advanced]
            )
        for Page in pages:
            page = Page()
            page.show()
            notebook.append_page(page)
        if len(pages) > 1:
            add_css(notebook, "tab { padding: 6px 24px } ")
        else:
            notebook.set_show_tabs(False)

        if open_page in [page.name for page in pages]:
            self.set_page(open_page)
        else:
            page_name = config.get("memory", "prefs_page", "")
            self.set_page(page_name)

        def on_switch_page(notebook, page, page_num):
            config.set("memory", "prefs_page", page.name)

        notebook.connect("switch-page", on_switch_page)

        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        connect_obj(close, "clicked", lambda x: x.destroy(), self)
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

        connect_obj(self, "destroy", PreferencesWindow.__destroy, self)

        self.get_child().show_all()

    def set_page(self, name):
        notebook = self.__notebook
        for p in range(notebook.get_n_pages()):
            if notebook.get_nth_page(p).name == name:
                notebook.set_current_page(p)

    def __destroy(self):
        config.save()
        new_dirs = set(get_scan_dirs())
        gone_dirs = set(self.current_scan_dirs) - new_dirs
        if new_dirs - set(self.current_scan_dirs):
            print_d("Library paths have been added, re-scanning...")
            scan_library(app.library, force=False)
        elif gone_dirs:
            copool.add(app.librarian.remove_roots, gone_dirs)


def create_grid(column_spacing: int = 12, row_spacing: int = 6):
    return Gtk.Grid(row_spacing=row_spacing, column_spacing=column_spacing)


def hbox_for(label: Gtk.Label, entry: Gtk.Entry, expand_entry: bool = True) -> Gtk.Box:
    hb = Gtk.Box(spacing=12)
    hb.pack_start(label, False, False, 0)
    hb.pack_end(entry, expand_entry, True, 0)
    return hb
