# Copyright 2005-2009 Joe Wreschnig, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gobject
import random
import math

from quodlibet import config, player, widgets, util
try:
    from quodlibet.qltk import notif
except:
    notif = None
from quodlibet.plugins.events import EventPlugin

class RandomAlbum(EventPlugin):
    PLUGIN_ID = 'Random Album Playback'
    PLUGIN_NAME = _('Random Album Playback')
    PLUGIN_DESC = ("When your playlist reaches its end a new album will "
                   "be chosen randomly and started. It requires that your "
                   "active browser supports filtering by album.")
    PLUGIN_VERSION = '2.3'

    weights = {}
    use_weights = False
    # Not a dict because we want to impose a particular order
    keys = [
                ("rating", _("Rated higher")),
                ("playcount", _("Played more often")),
                ("skipcount", _("Skipped more often")),
                ("lastplayed", _("Played more recently")),
                ("laststarted", _("Started more recently")),
                ("added", _("Added more recently")),
            ]

    def __init__(self):
        for (key, text) in self.keys:
            try: val = config.getfloat("plugins", "randomalbum_%s" % key)
            except config.error: val = 0
            self.weights[key] = val

        try: use = config.getint("plugins", "randomalbum_use_weights")
        except config.error: use = 0
        self.use_weights = use
        try: delay = config.getint("plugins", "randomalbum_delay")
        except config.error: delay = 0
        self.delay = delay

    def PluginPreferences(self, song):
        def changed_cb(hscale, key):
            val = hscale.get_value()
            self.weights[key] = val
            config.set("plugins", "randomalbum_%s" % key, val)

        def delay_changed_cb(spin):
            self.delay = int(spin.get_value())
            config.set("plugins", "randomalbum_delay", str(self.delay))

        def toggled_cb(check, table):
            self.use_weights = check.get_active()
            table.set_sensitive(self.use_weights)
            config.set("plugins", "randomalbum_use_weights",
                    str(int(self.use_weights)))

        vbox = gtk.VBox()
        table = gtk.Table(len(self.keys) + 1, 3)

        hbox = gtk.HBox(spacing=6)
        spin = gtk.SpinButton(gtk.Adjustment(self.delay, 0, 3600, 1, 10))
        spin.connect("value-changed", delay_changed_cb)
        hbox.pack_start(spin, expand=False)
        lbl = gtk.Label(_("Wait before starting next album"))
        hbox.pack_start(lbl, expand=False)
        vbox.pack_start(hbox)

        check = gtk.CheckButton(_("Play some albums more than others"))
        vbox.pack_start(check, expand=False)
        check.connect("toggled", toggled_cb, table)
        check.set_active(self.use_weights)
        toggled_cb(check, table)

        frame = gtk.Frame(_("Weights"))
        frame.add(table)
        vbox.pack_start(frame)

        less_lbl = gtk.Label(_("avoid"))
        less_lbl.set_alignment(0, 0)
        table.attach(less_lbl, 1, 2, 0, 1)
        more_lbl = gtk.Label(_("prefer"))
        more_lbl.set_alignment(1, 0)
        table.attach(more_lbl, 2, 3, 0, 1)

        for (idx, (key, text)) in enumerate(self.keys):
            lbl = gtk.Label(text)
            lbl.set_alignment(0, 0)
            table.attach(lbl, 0, 1, idx + 1, idx + 2, xoptions = gtk.FILL)

            adj = gtk.Adjustment(lower=-1.0, upper=1.0, step_incr=0.1)
            hscale = gtk.HScale(adj)
            hscale.set_value(self.weights[key])
            hscale.set_draw_value(False)
            hscale.set_show_fill_level(False)
            hscale.connect("value-changed", changed_cb, key)
            table.attach(hscale, 1, 3, idx + 1, idx + 2)

        return vbox

    def _score(self, album_names):
        """Score each album. Returns a list of (score, name) tuples."""
        from library import library

        # Find the songs for each album name, and extract keys being measured
        albums = {}
        for song in library:
            if song('album') in album_names:
                vsong = {}
                for (key, text) in self.keys:
                    vsong[key] = song("~#%s" % key)
                albums.setdefault(song('album'), []).append(vsong)

        # Find the mean value for each key across all songs in an album
        for name, songs in albums.items():
            mean = {}
            for key, text in self.keys:
                mean[key] = sum(map(lambda s: s.get(key, 0), songs))/len(songs)
            albums[name] = mean

        # Score the album based on its weighted rank ordering for each key
        # Rank ordering is more resistant to clustering than weighting
        # based on normalized means, and also normalizes the scale of each
        # weight slider in the prefs pane.
        scores = {}
        for key, text in self.keys:
            names = sorted(albums.keys(), key = lambda n: albums[n].get(key))
            for i, name in enumerate(names):
                scores[name] = scores.get(name, 0) + i * self.weights[key]

        return [(score, name) for name, score in scores.items()]

    def plugin_on_song_started(self, song):
        if (song is None and config.get("memory", "order") != "onesong" and
            not player.playlist.paused):
            browser = widgets.main.browser
            if not browser.can_filter('album'): return

            # Unfortunately, browsers can't (yet) filter on the album key
            try: values = browser.list('album')
            except AttributeError:
                from library import library
                values = library.tag_values('album')
            if not values: return

            if self.use_weights:
                # Select 3% of albums, or at least 3 albums
                nr_albums = int(min(len(values), max(0.03 * len(values), 3)))
                album_names = random.sample(values, nr_albums)
                albums = sorted(self._score(album_names))
                for score, name in albums:
                    print_d("randomalbum.py: %0.4f %s" % (score, name))
                album = max(albums)[1]
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
                              _("Waiting to start <i>%s</i>") % album,
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
        browser = widgets.main.browser
        if not browser.can_filter('album'): return
        browser.filter('album', [album])
        gobject.idle_add(self.unpause)

    def unpause(self):
        # Wait for the next GTK loop to make sure everything's tidied up
        # after the song ended. Also, if this is program startup and the
        # previous current song wasn't found, we'll get this condition
        # as well, so just leave the player paused if that's the case.
        try: player.playlist.next()
        except AttributeError: player.playlist.paused = True
