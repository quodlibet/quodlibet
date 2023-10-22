# Copyright 2005-2009 Joe Wreschnig, Steven Robertson
#           2012-2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import random
from typing import Dict

from gi.repository import Gtk, GLib

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet.plugins.events import EventPlugin
from quodlibet import util
from quodlibet.util import print_d
from quodlibet.browsers.playlists import PlaylistsBrowser
from quodlibet.qltk import notif, Icons


class RandomAlbum(EventPlugin):
    PLUGIN_ID = "Random Album Playback"
    PLUGIN_NAME = _("Random Album Playback")
    PLUGIN_DESC = _("Starts a random album when your playlist reaches its "
                    "end. It requires that your active browser supports "
                    "filtering by album.")
    PLUGIN_ICON = Icons.MEDIA_SKIP_FORWARD

    weights: Dict[str, float] = {}
    use_weights = False
    # Not a dict because we want to impose a particular order
    # Third item is to specify a non-default aggregation function
    keys = [
                ("rating", _("Rated higher"), None),
                ("playcount", _("Played more often"), "avg"),
                ("skipcount", _("Skipped more often"), "avg"),
                ("lastplayed", _("Played more recently"), None),
                ("laststarted", _("Started more recently"), None),
                ("added", _("Added more recently"), None),
                ("length", _("Longer albums"), None),
            ]

    def __init__(self):
        for (key, _text, _func) in self.keys:
            val = config.getfloat("plugins", "randomalbum_%s" % key, 0.0)
            self.weights[key] = val

        use = config.getint("plugins", "randomalbum_use_weights", 0)
        self.use_weights = use
        delay = config.getint("plugins", "randomalbum_delay", 0)
        self.delay = delay

    def PluginPreferences(self, song):
        def changed_cb(hscale, key):
            val = hscale.get_value()
            self.weights[key] = val
            config.set("plugins", "randomalbum_%s" % key, val)

        def delay_changed_cb(spin):
            self.delay = int(spin.get_value())
            config.set("plugins", "randomalbum_delay", str(self.delay))

        def toggled_cb(check, widgets):
            self.use_weights = check.get_active()
            for w in widgets:
                w.set_sensitive(self.use_weights)
            config.set("plugins", "randomalbum_use_weights",
                    str(int(self.use_weights)))

        vbox = Gtk.VBox(spacing=12)
        table = Gtk.Table(n_rows=len(self.keys) + 1, n_columns=3)
        table.set_border_width(3)

        hbox = Gtk.HBox(spacing=6)
        spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment.new(self.delay, 0, 3600, 1, 10, 0))
        spin.connect("value-changed", delay_changed_cb)
        hbox.pack_start(spin, False, True, 0)
        lbl = Gtk.Label(label=_("seconds before starting next album"))
        hbox.pack_start(lbl, False, True, 0)
        vbox.pack_start(hbox, True, True, 0)

        frame = Gtk.Frame(label=_("Weights"))

        check = Gtk.CheckButton(label=_("Play some albums more than others"))
        vbox.pack_start(check, False, True, 0)
        # Toggle both frame and contained table; frame doesn't always work?
        check.connect("toggled", toggled_cb, [frame, table])
        check.set_active(self.use_weights)
        toggled_cb(check, [frame, table])

        frame.add(table)
        vbox.pack_start(frame, True, True, 0)

        # Less label
        less_lbl = Gtk.Label()
        arr = Gtk.Arrow(arrow_type=Gtk.ArrowType.LEFT,
                        shadow_type=Gtk.ShadowType.OUT)
        less_lbl.set_markup(util.italic(_("avoid")))
        less_lbl.set_alignment(0, 0)
        hb = Gtk.HBox(spacing=0)
        hb.pack_start(arr, False, True, 0)
        hb.pack_start(less_lbl, True, True, 0)
        table.attach(hb, 1, 2, 0, 1, xpadding=3,
                     xoptions=Gtk.AttachOptions.FILL)
        # More label
        more_lbl = Gtk.Label()
        arr = Gtk.Arrow(arrow_type=Gtk.ArrowType.RIGHT,
                        shadow_type=Gtk.ShadowType.OUT)
        more_lbl.set_markup(util.italic(_("prefer")))
        more_lbl.set_alignment(1, 0)
        hb = Gtk.HBox(spacing=0)
        hb.pack_end(arr, False, True, 0)
        hb.pack_end(more_lbl, True, True, 0)
        table.attach(hb, 2, 3, 0, 1, xpadding=3,
                     xoptions=Gtk.AttachOptions.FILL)

        for (idx, (key, text, _func)) in enumerate(self.keys):
            lbl = Gtk.Label(label=text)
            lbl.set_alignment(0, 0)
            table.attach(lbl, 0, 1, idx + 1, idx + 2,
                         xoptions=Gtk.AttachOptions.FILL,
                         xpadding=3, ypadding=3)
            adj = Gtk.Adjustment(lower=-1.0, upper=1.0, step_increment=0.1)
            hscale = Gtk.HScale(adjustment=adj)
            hscale.set_value(self.weights[key])
            hscale.set_draw_value(False)
            hscale.set_show_fill_level(False)
            hscale.connect("value-changed", changed_cb, key)
            lbl.set_mnemonic_widget(hscale)
            table.attach(hscale, 1, 3, idx + 1, idx + 2,
                         xpadding=3, ypadding=3)

        return vbox

    def _score(self, albums):
        """Score each album. Returns a list of (score, album) tuples."""

        # Score the album based on its weighted rank ordering for each key
        # Rank ordering is more resistant to clustering than weighting
        # based on normalized means, and also normalizes the scale of each
        # weight slider in the prefs pane.
        ranked = {}
        for (tag, _text, func) in self.keys:
            tag_key = ("~#%s:%s" % (tag, func) if func
                       else "~#%s" % tag)
            ranked[tag] = sorted(albums,
                                 key=lambda al: al.get(tag_key))

        scores = {}
        for album in albums:
            scores[album] = 0
            for (tag, _text, _func) in self.keys:
                rank = ranked[tag].index(album)
                scores[album] += rank * self.weights[tag]

        return [(score, album) for album, score in scores.items()]

    def plugin_on_song_started(self, song):
        one_song = app.player_options.single
        if song is None and not one_song and not app.player.paused:
            browser = app.window.browser

            if self.disabled_for_browser(browser):
                print_d("%s doesn't support album filtering" % browser.name)
                return

            albumlib = app.library.albums
            albumlib.load()

            if browser.can_filter_albums():
                keys = browser.list_albums()
                values = [albumlib[k] for k in keys]
            else:
                keys = set(browser.list("album"))
                values = [a for a in albumlib if a("album") in keys]
            if not values:
                print_d("No albums to randomly choose from.")
                return

            if self.use_weights:
                # Select 3% of albums, or at least 3 albums
                total = len(values)
                nr_albums = min(total, max(int(0.03 * total), 3))
                print_d("Choosing from %d library albums:" % nr_albums)
                chosen_albums = random.sample(values, nr_albums)
                album_scores = self._score(chosen_albums)
                # Find highest score value
                max_score = max(album_scores, key=lambda t: t[0])[0]
                print_d("Maximum score found: %0.1f" % max_score)
                # Filter albums by highest score value
                albums = [(sc, al)
                          for sc, al in album_scores
                          if sc == max_score]
                print_d("Albums with maximum score:")
                for _score, album in albums:
                    print_d("  %s" % album("album"))

                # Pick random album from list of highest scored albums
                album = random.choice(albums)[1]
            else:
                album = random.choice(values)

            if album is not None:
                print_d("Chosen album: %s" % album("album"))
                self.schedule_change(album)

    def schedule_change(self, album):
        if self.delay:
            srcid = GLib.timeout_add(1000 * self.delay,
                                     self.change_album, album)
            task = notif.Task(_("Random Album"),
                              _("Waiting to start %s") % util.bold(album("album")),
                              stop=lambda: GLib.source_remove(srcid))

            def countdown():
                for i in range(10 * self.delay):
                    task.update(i / (10. * self.delay))
                    yield True
                task.finish()
                yield False
            GLib.timeout_add(100, next, countdown())
        else:
            self.change_album(album)

    def change_album(self, album):
        browser = app.window.browser
        if self.disabled_for_browser(browser):
            return

        if browser.can_filter_albums():
            browser.filter_albums([album.key])
        else:
            browser.filter("album", [album("album")])
        GLib.idle_add(self.unpause)

    def unpause(self):
        # Wait for the next GTK loop to make sure everything's tidied up
        # after the song ended. Also, if this is program startup and the
        # previous current song wasn't found, we'll get this condition
        # as well, so just leave the player paused if that's the case.
        try:
            app.player.next()
        except AttributeError:
            app.player.paused = True

    def disabled_for_browser(self, browser):
        return (not browser.can_filter("album") or
                isinstance(browser, PlaylistsBrowser))
