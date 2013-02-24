# Copyright 2005-2009 Joe Wreschnig, Steven Robertson
#                2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import random

import gtk
import gobject

from quodlibet import app
from quodlibet import config
from quodlibet.plugins.events import EventPlugin
from quodlibet import util
try: from quodlibet.qltk import notif
except Exception: notif = None

class RandomAlbum(EventPlugin):
    PLUGIN_ID = 'Random Album Playback'
    PLUGIN_NAME = _('Random Album Playback')
    PLUGIN_DESC = ("When your playlist reaches its end a new album will "
                   "be chosen randomly and started. It requires that your "
                   "active browser supports filtering by album.")
    PLUGIN_VERSION = '2.4'

    weights = {}
    use_weights = False
    # Not a dict because we want to impose a particular order
    # Third item is to specify a non-default aggregation function
    keys = [
                ("rating", _("Rated higher"), None),
                ("playcount", _("Played more often"), 'avg'),
                ("skipcount", _("Skipped more often"), 'avg'),
                ("lastplayed", _("Played more recently"), None),
                ("laststarted", _("Started more recently"), None),
                ("added", _("Added more recently"), None),
                ("length", _("Longer albums"), None),
            ]

    def __init__(self):
        for (key, text, func) in self.keys:
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

        vbox = gtk.VBox(spacing=12)
        table = gtk.Table(len(self.keys) + 1, 3)
        table.set_border_width(3)

        hbox = gtk.HBox(spacing=6)
        spin = gtk.SpinButton(gtk.Adjustment(self.delay, 0, 3600, 1, 10))
        spin.connect("value-changed", delay_changed_cb)
        hbox.pack_start(spin, expand=False)
        lbl = gtk.Label(_("seconds before starting next album"))
        hbox.pack_start(lbl, expand=False)
        vbox.pack_start(hbox)

        frame = gtk.Frame(_("Weights"))

        check = gtk.CheckButton(_("Play some albums more than others"))
        vbox.pack_start(check, expand=False)
        # Toggle both frame and contained table; frame doesn't always work?
        check.connect("toggled", toggled_cb, [frame,table])
        check.set_active(self.use_weights)
        toggled_cb(check, [frame,table])

        frame.add(table)
        vbox.pack_start(frame)

        # Less label
        less_lbl = gtk.Label()
        arr = gtk.Arrow(gtk.ARROW_LEFT, gtk.SHADOW_OUT)
        less_lbl.set_markup("<i>%s</i>" % util.escape(_("avoid")))
        less_lbl.set_alignment(0, 0)
        hb = gtk.HBox(spacing=0)
        hb.pack_start(arr, expand=False)
        hb.pack_start(less_lbl)
        table.attach(hb, 1, 2, 0, 1, xpadding=3, xoptions=gtk.FILL)
        # More label
        more_lbl = gtk.Label()
        arr = gtk.Arrow(gtk.ARROW_RIGHT, gtk.SHADOW_OUT)
        more_lbl.set_markup("<i>%s</i>" % util.escape(_("prefer")))
        more_lbl.set_alignment(1, 0)
        hb = gtk.HBox(spacing=0)
        hb.pack_end(arr, expand=False)
        hb.pack_end(more_lbl)
        table.attach(hb, 2, 3, 0, 1, xpadding=3, xoptions=gtk.FILL)

        for (idx, (key, text, func)) in enumerate(self.keys):
            lbl = gtk.Label(text)
            lbl.set_alignment(0, 0)
            table.attach(lbl, 0, 1, idx + 1, idx + 2,
                         xoptions=gtk.FILL, xpadding=3, ypadding=3)
            adj = gtk.Adjustment(lower=-1.0, upper=1.0, step_incr=0.1)
            hscale = gtk.HScale(adj)
            hscale.set_value(self.weights[key])
            hscale.set_draw_value(False)
            hscale.set_show_fill_level(False)
            hscale.connect("value-changed", changed_cb, key)
            lbl.set_mnemonic_widget(hscale)
            table.attach(hscale, 1, 3, idx + 1, idx + 2, xpadding=3, ypadding=3)

        return vbox

    def _score(self, albums):
        """Score each album. Returns a list of (score, name) tuples."""

        # Score the album based on its weighted rank ordering for each key
        # Rank ordering is more resistant to clustering than weighting
        # based on normalized means, and also normalizes the scale of each
        # weight slider in the prefs pane.
        ranked = {}
        for (tag, text, func) in self.keys:
            tag_key = ("~#%s:%s" % (tag, func) if func
                       else "~#%s" % tag)
            ranked[tag] = sorted(albums,
                                 key=lambda al: al.get(tag_key))

        scores = {}
        for album in albums:
            scores[album] = 0
            for (tag, text, func) in self.keys:
                rank = ranked[tag].index(album)
#                print_d("%s: ranked %d out of %d (with %s) for %s = +%d points"
#                        % (album("album"), rank+1,len(albums),
#                           album("~#%s" % tag), tag, rank * self.weights[tag]))
                scores[album] += rank * self.weights[tag]

        return [(score, name) for name, score in scores.items()]

    def plugin_on_song_started(self, song):
        if (song is None and config.get("memory", "order") != "onesong" and
            not app.player.paused):
            browser = app.window.browser

            if not browser.can_filter('album'):
                return

            albumlib = app.library.albums
            albumlib.load()

            if browser.can_filter_albums():
                keys = browser.list_albums()
                values = [albumlib[k] for k in keys]
            else:
                keys = set(browser.list("album"))
                values = [a for a in albumlib if a("album") in keys]

            if self.use_weights:
                # Select 3% of albums, or at least 3 albums
                nr_albums = int(min(len(values), max(0.03 * len(values), 3)))
                chosen_albums = random.sample(values, nr_albums)
                album_scores = sorted(self._score(chosen_albums))
                for score, album in album_scores:
                    print_d("%0.2f scored by %s" % (score, album("album")))
                album = max(album_scores)[1]
            else:
                album = random.choice(values)

            if album is not None:
                self.schedule_change(album)

    def schedule_change(self, album):
        if self.delay:
            srcid = gobject.timeout_add(1000 * self.delay,
                                        self.change_album, album)
            if notif is None: return
            task = notif.Task(_("Random Album"),
                              _("Waiting to start <i>%s</i>") % album("album"),
                              stop=lambda: gobject.source_remove(srcid))
            def countdown():
                for i in range(10 * self.delay):
                    task.update(i / (10. * self.delay))
                    yield True
                task.finish()
                yield False
            gobject.timeout_add(100, countdown().next)
        else:
            self.change_album(album)

    def change_album(self, album):
        browser = app.window.browser
        if not browser.can_filter('album'):
            return

        if browser.can_filter_albums():
            browser.filter_albums([album.key])
        else:
            browser.filter('album', [album("album")])
        gobject.idle_add(self.unpause)

    def unpause(self):
        # Wait for the next GTK loop to make sure everything's tidied up
        # after the song ended. Also, if this is program startup and the
        # previous current song wasn't found, we'll get this condition
        # as well, so just leave the player paused if that's the case.
        try: app.player.next()
        except AttributeError: app.player.paused = True
