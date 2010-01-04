# Copyright 2005-2009 Joe Wreschnig, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gobject
import random
import math

from quodlibet import config, player, widgets
from quodlibet.plugins.events import EventPlugin

class RandomAlbum(EventPlugin):
    PLUGIN_ID = 'Random Album Playback'
    PLUGIN_NAME = _('Random Album Playback')
    PLUGIN_DESC = ("When your playlist reaches its end a new album will "
                   "be chosen randomly and started. It requires that your "
                   "active browser supports filtering by album.")
    PLUGIN_VERSION = '2.2'

    weights = {}
    use_weights = False
    # Not a dict because we want to impose a particular order
    keys = [
                ("rating", _("Rated higher")),
                ("playcount", _("Played more often")),
                ("skipcount", _("Skipped more often")),
                ("lastplayed", _("Played more recently")),
                ("laststarted", _("Last started playing")),
                ("added", _("First added to library")),
            ]

    def __init__(self):
        for (key, text) in self.keys:
            try: val = config.getfloat("plugins", "randomalbum_%s" % key)
            except: val = 0
            self.weights[key] = val

        try: use = config.getint("plugins", "randomalbum_use_weights")
        except: use = 0
        self.use_weights = use

    def PluginPreferences(self, song):
        def changed_cb(hscale, key):
            val = hscale.get_value()
            self.weights[key] = val
            config.set("plugins", "randomalbum_%s" % key, val)

        def toggled_cb(check, table):
            self.use_weights = check.get_active()
            table.set_sensitive(self.use_weights)
            config.set("plugins", "randomalbum_use_weights",
                    str(int(self.use_weights)))

        vbox = gtk.VBox()
        table = gtk.Table(len(self.keys) + 1, 3)

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

    def _eval_keys(self, songs):
        # Returns a dict containing the key values for a set of songs
        album = {}
        for (key, text) in self.keys:
            if key == 'laststarted':
                # The only key evaluated as a max, rather than a mean
                v = [max(s['~#laststarted'], s['~#added']) for s in songs]
                album[key] = max(v)
            else:
                if key == 'lastplayed':
                    # This gets special handling for songs with lastplayed=0
                    v = [max(s['~#lastplayed'], s['~#added']) for s in songs]
                else:
                    v = [s['~#%s' % key] for s in songs]
                album[key] = sum(v)/float(len(v))
        return album

    def _score(self, album_names):
        # Score each album. It works out to be this:
        #     score = sum([normalized_value[key] * weight[key]])
        # and most of this code just finds the normalized values.
        from library import library
        album_songs = {}
        for song in library:
            if song('album') in album_names:
                album_songs.setdefault(song('album'), []).append(song)

        albums = {}
        for name, songs in album_songs.items():
            albums[name] = self._eval_keys(songs)

        ranges = {}
        for (key, text) in self.keys:
            scores = [album[key] for album in albums.values()]
            ranges[key] = (min(scores), max(scores))

        scored = []
        for name, album in albums.items():
            score = 0
            for key, val in album.items():
                (minn, maxx) = ranges[key]
                if maxx > minn:
                    normalized = (val - minn) / (maxx - minn)
                    score += normalized * self.weights[key]
            # If someone enables weights and has a very small preference set,
            # that preference will have a disproportionate effect on the
            # selection process, so we offset that here.
            score += random.random() / 16
            scored.append((score, name))
            print_d('randomalbum.py: Album "%s", score %f' % (name, score))
        return scored

    def plugin_on_song_started(self, song):
        if (song is None and config.get("memory", "order") != "onesong" and
            not player.playlist.paused):
            browser = widgets.main.browser
            if not browser.can_filter('album'): return

            try: values = browser.list('album')
            except AttributeError:
                from library import library
                values = library.tag_values('album')
            if not values: return

            if self.use_weights:
                # Select 3% of albums, or at least 3 albums
                nr_albums = int(min(len(values), max(0.03 * len(values), 3)))
                album_names = random.sample(values, nr_albums)
                album = max(self._score(album_names))[1]
            else:
                album = random.choice(values)
            if album is not None:
                browser.filter('album', [album])
                gobject.idle_add(self.unpause)

    def unpause(self):
        # Wait for the next GTK loop to make sure everything's tidied up
        # after the song ended. Also, if this is program startup and the
        # previous current song wasn't found, we'll get this condition
        # as well, so just leave the player paused if that's the case.
        try: player.playlist.next()
        except AttributeError: player.playlist.paused = True
