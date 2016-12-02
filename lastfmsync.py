# -*- coding: utf-8 -*-
# Copyright 2010 Steven Robertson
#           2016 Mice Pápai
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import shelve
import urllib
import urllib2
import time
from datetime import date
from threading import Thread
import Queue

from gi.repository import Gtk, GLib, GObject

import quodlibet
from quodlibet import _
from quodlibet import config, util, qltk
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk import Icons
from quodlibet.qltk.notif import Task
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util import copool
from quodlibet.util.i18n import numeric_phrase
from quodlibet.util.dprint import print_d

try:
    import json
except ImportError:
    import simplejson as json

API_KEY = "f536cdadb4c2aec75ae15e2b719cb3a1"


def log(msg):
    util.print_d('[lastfmsync] %s' % msg)


def apicall(method, **kwargs):
    """Performs Last.fm API call."""
    real_args = {
        'api_key': API_KEY,
        'format': 'json',
        'method': method,
    }
    real_args.update(kwargs)
    url = ''.join(["https://ws.audioscrobbler.com/2.0/?",
                   urllib.urlencode(real_args)])
    log(url)
    uobj = urllib2.urlopen(url)
    resp = json.load(uobj)
    if 'error' in resp:
        errmsg = 'Last.fm API error: %s' % resp.get('message', '')
        log(errmsg)
        raise EnvironmentError(resp['error'], errmsg)
    return resp


def config_get(key, default=None):
    return config.get('plugins', 'lastfmsync_%s' % key, default)


class LastFMSyncCache(object):
    """Stores the Last.fm charts for a particular user."""

    def __init__(self, username):
        self.username = username
        self.lastupdated = None
        self.registered = 0
        self.progress = 0
        self.maxprogress = 0
        self.charts = {}
        self.songs = {}

    def update_charts(self, progress=None):
        """Updates Last.fm charts for the given user. Returns True if an
        update was attempted, False otherwise.

        progress is a callback func (msg, frac) that will be called to
        update a UI. 'frac' may be None to indicate no change should be made.
        If the function returns False, this thread will stop early."""

        def prog(msg, frac):
            if progress:
                if not progress(msg, frac):
                    # this gets caught later
                    raise ValueError()

        try:
            # Last.fm updates their charts weekly; we only poll for new
            # charts if it's been more than a day since the last poll
            if self.registered == 0:
                resp = apicall('user.getinfo', user=self.username)
                self.registered = int(resp['user']['registered']['unixtime'])

            now = time.time()
            if not self.lastupdated or self.lastupdated + (24 * 60 * 60) < now:
                prog(_("Updating chart list."), 0)
                resp = apicall('user.getweeklychartlist', user=self.username)
                charts = resp['weeklychartlist']['chart']
                for chart in charts:
                    # Charts keys are 2-tuple (from_timestamp, to_timestamp);
                    # values are whether we still need to fetch the chart
                    fro, to = map(lambda s: int(chart[s]), ('from', 'to'))

                    # If the chart is older than the register date of the
                    # user, don't download it. (So the download doesn't start
                    # with ~2005 every time.)
                    if to < self.registered:
                        continue

                    self.charts.setdefault((fro, to), True)
                self.lastupdated = now
            elif not filter(None, self.charts.values()):
                # No charts to fetch, no update scheduled.
                prog(_("Already up-to-date."), 1.)
                return False

            new_charts = filter(lambda k: self.charts[k], self.charts.keys())

            job_queue = Queue.Queue()
            result_queue = Queue.Queue()
            for i in range(4):
                worker = Thread(
                    target=self.get_weekly_track_chart_worker,
                    args=(job_queue, result_queue,),
                    name='worker-{}'.format(i),
                )
                worker.setDaemon(True)
                worker.start()

            self.maxprogress = len(new_charts)
            for idx, (fro, to) in enumerate(sorted(new_charts)):
                args = {'user': self.username, 'from': fro, 'to': to}
                job_queue.put(args)

                # http://www.last.fm/api/tos
                # 5 requests / sec
                time.sleep(0.2)

            job_queue.join()

            while not result_queue.empty():
                tracks = result_queue.get()
                for track in tracks:
                    self._update_stats(track, fro, to)
                self.charts[(fro, to)] = False

            prog(_("Sync complete."), 1.)
        except ValueError:
            # this is probably from prog()
            pass
        except Exception:
            util.print_exc()
            prog(_("Error during sync"), None)
            return False

        return True

    def get_weekly_track_chart_worker(self, job_queue, result_queue):
        while True:
            args = job_queue.get()

            self.progress += 1
            chart_week = date.fromtimestamp(args['from']).isoformat()
            #self.prog(_("Fetching chart for week of %s.") % chart_week,
            #          (self.progress + 1.) / (self.maxprogress + 2.))

            result_queue.put(self.get_weekly_track_chart(args))

            job_queue.task_done()

    def get_weekly_track_chart(self, args):
        try:
            resp = apicall('user.getweeklytrackchart', **args)
        except urllib2.HTTPError as err:
            msg = "HTTP error %d, retrying in %d seconds."
            log(msg % (err.code, 15))
            for i in range(15, 0, -1):
                time.sleep(1)
                self.prog(msg % (err.code, i), None)
            resp = apicall('user.getweeklytrackchart', **args)
        try:
            tracks = resp['weeklytrackchart']['track']
        except KeyError:
            tracks = []

        # Delightfully, the API JSON frontend unboxes 1-element lists.
        if isinstance(tracks, dict):
            tracks = [tracks]

        return tracks

    def _update_stats(self, track, chart_fro, chart_to):
        """Updates a single track's stats. 'track' is as returned by API;
        'chart_fro' and 'chart_to' are the chart's timestamp range."""

        # we try track mbid, (artist mbid, name), (artist name, name) as keys
        keys = []
        if track['mbid']:
            keys.append(track['mbid'])
        for artist in (track['artist']['mbid'], track['artist']['#text']):
            if artist:
                keys.append((artist.lower(), track['name'].lower()))

        stats = filter(None, map(self.songs.get, keys))
        if stats:
            # Not sure if last.fm ever changes their tag values, but this
            # should map all changed values to the same object correctly
            plays = max(map(lambda d: d.get('playcount', 0), stats))
            last = max(map(lambda d: d.get('lastplayed', 0), stats))
            added = max(map(lambda d: d.get('added', chart_to), stats))
            stats = stats[0]
            stats.update(
                {'playcount': plays, 'lastplayed': last, 'added': added})
        else:
            stats = {'playcount': 0, 'lastplayed': 0, 'added': chart_to}

        stats['playcount'] += int(track['playcount'])
        stats['lastplayed'] = max(stats['lastplayed'], chart_fro)
        stats['added'] = min(stats['added'], chart_to)

        for key in keys:
            self.songs[key] = stats

    def update_songs(self, songs):
        """Updates each SongFile in songs from the cache."""
        for song in songs:
            keys = []
            if 'musicbrainz_trackid' in song:
                keys.append(song['musicbrainz_trackid'].lower())
            if 'musiscbrainz_artistid' in song:
                keys.append((song['musicbrainz_artistid'].lower(),
                             song.get('title', '').lower()))
            keys.append((song.get('artist', '').lower(),
                         song.get('title', '').lower()))
            stats = filter(None, map(self.songs.get, keys))
            if not stats:
                continue
            stats = stats[0]

            playcount = max(song.get('~#playcount', 0), stats['playcount'])
            if playcount != 0:
                song['~#playcount'] = playcount
            lastplayed = max(song.get('~#lastplayed', 0), stats['lastplayed'])
            if lastplayed != 0:
                song['~#lastplayed'] = lastplayed
            song['~#added'] = min(song['~#added'], stats['added'])

    def update_songs2(self, songs):
        def need_yield(last_yield=[0]):
            current = time.time()
            if abs(current - last_yield[0]) > 0.015:
                last_yield[0] = current
                return True
            return False

        def check_songs2():
            desc = numeric_phrase("%d song", "%d songs", len(songs))
            with Task(_("Last.fm Sync"), desc) as task:
                task.copool(check_songs2)

                for i, song in enumerate(songs):
                    time.sleep(1)
                    task.update((float(i) + 1) / len(songs))

                    print_d("yololo local branch {0}".format(song.get('title')))

                    keys = []
                    if 'musicbrainz_trackid' in song:
                        keys.append(song['musicbrainz_trackid'].lower())
                    if 'musiscbrainz_artistid' in song:
                        keys.append((song['musicbrainz_artistid'].lower(),
                                     song.get('title', '').lower()))
                    keys.append((song.get('artist', '').lower(),
                                 song.get('title', '').lower()))
                    stats = filter(None, map(self.songs.get, keys))

                    if not stats:
                        continue

                    stats = stats[0]

                    playcount = max(song.get('~#playcount', 0),
                                    stats['playcount'])
                    if playcount != 0:
                        song['~#playcount'] = playcount

                    lastplayed = max(song.get('~#lastplayed', 0),
                                     stats['lastplayed'])
                    if lastplayed != 0:
                        song['~#lastplayed'] = lastplayed

                    song['~#added'] = min(song['~#added'], stats['added'])

                    if need_yield():
                        task.pulse()
                        yield
            yield

        copool.add(check_songs2)


class LastFMSync(SongsMenuPlugin):
    PLUGIN_ID = "Last.fm Sync"
    PLUGIN_NAME = _("Last.fm Sync")
    PLUGIN_DESC = _("Updates your library's statistics from your "
                    "Last.fm profile.")
    PLUGIN_ICON = Icons.EMBLEM_SHARED

    CACHE_PATH = os.path.join(quodlibet.get_user_dir(), "lastfmsync.db")

    def plugin_songs(self, songs):

        self.cache_shelf = shelve.open(self.CACHE_PATH)
        user = config_get('username', '')
        try:
            cache = self.cache_shelf.setdefault(user, LastFMSyncCache(user))
        except Exception:
            # unpickle can fail in many ways. this is just cache, so ignore
            cache = self.cache_shelf[user] = LastFMSyncCache(user)

        cache.update_songs2(songs)



    @classmethod
    def PluginPreferences(klass, win):
        def entry_changed(entry):
            config.set('plugins', 'lastfmsync_username', entry.get_text())

        label = Gtk.Label(label=_("_Username:"), use_underline=True)
        entry = UndoEntry()
        entry.set_text(config_get('username', ''))
        entry.connect('changed', entry_changed)
        label.set_mnemonic_widget(entry)

        hbox = Gtk.HBox()
        hbox.set_spacing(6)
        hbox.pack_start(label, False, True, 0)
        hbox.pack_start(entry, True, True, 0)

        return qltk.Frame(_("Account"), child=hbox)
