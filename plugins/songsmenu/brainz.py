# brainz.py - Quod Libet plugin to tag files from MusicBrainz automatically
# Copyright 2005-2010   Joshua Kwan <joshk@triplehelix.org>,
#                       Michael Ball <michael.ball@gmail.com>,
#                       Steven Robertson <steven@strobe.cc>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import threading
import time

import gtk
import gobject
import pango

from quodlibet import config, util
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.views import HintedTreeView, MultiDragTreeView

from musicbrainz2 import webservice as ws
from musicbrainz2.utils import extractUuid
VARIOUS_ARTISTS_ARTISTID = '89ad4ac3-39f7-470e-963a-56509c546377'

def get_artist(album):
    """Returns a single artist likely to be the MB AlbumArtist, or None."""
    for tag in ["albumartist", "artist", "performer"]:
        names = set()
        for song in album:
            map(names.add, filter(lambda n: n, song.get(tag, "").split("\n")))
        if len(names) == 1:
            return names.pop()
        elif len(names) > 1:
            return None
    return None

def get_trackcount(album):
    """Returns the track count, hammered into submission."""
    return max(max(map(lambda t: max(map(int,
        t.get('tracknumber', '0').split('/'))), album)), len(album)) # (;))

def config_get(key, default=''):
    try:
        return config.getboolean('plugins', 'brainz_' + key)
    except config.error:
        return default

class ResultTreeView(HintedTreeView, MultiDragTreeView):
    """The result treeview. The model only stores local tracks; info about
    remote results is pulled from self.remote_album."""

    def __name_datafunc(self, col, cell, model, itr):
        song = model[itr][0]
        if song:
            cell.set_property('text', os.path.basename(song.get("~filename")))
        else:
            cell.set_property('text', '')

    def __track_datafunc(self, col, cell, model, itr):
        idx = model.get_path(itr)[0]
        if idx >= len(self.remote_album):
            cell.set_property('text', '')
        else:
            cell.set_property('text', idx + 1)

    def __title_datafunc(self, col, cell, model, itr):
        idx = model.get_path(itr)[0]
        if idx >= len(self.remote_album):
            cell.set_property('text', '')
        else:
            cell.set_property('text', self.remote_album[idx].title)

    def __artist_datafunc(self, col, cell, model, itr):
        idx = model.get_path(itr)[0]
        if idx >= len(self.remote_album) or not self.remote_album[idx].artist:
            cell.set_property('text', '')
        else:
            cell.set_property('text', self.remote_album[idx].artist.name)

    def __init__(self, album):
        self.album = album
        self.remote_album = []
        self.model = gtk.ListStore(object)
        map(self.model.append, zip(album))

        super(ResultTreeView, self).__init__(self.model)
        self.set_headers_clickable(True)
        self.set_rules_hint(True)
        self.set_reorderable(True)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        cols = [
                ('Filename', self.__name_datafunc, True),
                ('Track', self.__track_datafunc, False),
                ('Title', self.__title_datafunc, True),
                ('Artist', self.__artist_datafunc, True),
            ]

        for title, func, resize in cols:
            render = gtk.CellRendererText()
            render.set_property('ellipsize', pango.ELLIPSIZE_END)
            col = gtk.TreeViewColumn(title, render)
            col.set_cell_data_func(render, func)
            col.set_resizable(resize)
            col.set_expand(resize)
            self.append_column(col)

    def update_remote_album(self, remote_album):
        """Updates the TreeView, handling results with a different number of
        tracks than the album being tagged."""
        for i in range(len(self.model), len(remote_album)):
            self.model.append((None, ))
        for i in range(len(self.model), len(remote_album), -1):
            if self.model[-1][0] is not None:
                break
            itr = self.model.get_iter_from_string(str(len(self.model) - 1))
            self.model.remove(itr)
        self.remote_album = remote_album
        has_artists = bool(filter(lambda t: t.artist, remote_album))
        self.get_column(3).set_visible(has_artists)
        self.columns_autosize()
        self.queue_draw()

class ResultComboBox(gtk.ComboBox):
    """Formatted picker for different Result entries."""

    def __init__(self, model):
        super(ResultComboBox, self).__init__(model)
        render = gtk.CellRendererText()
        render.set_fixed_height_from_font(2)
        def celldata(layout, cell, model, iter):
            release = model[iter][0]
            if not release:
                return
            date = release.getEarliestReleaseDate()
            if date:
                date = '%s, ' % date
            else:
                date = ''
            markup = "<b>%s</b>\n%s - %s%s tracks" % (
                    util.escape(release.title),
                    util.escape(release.artist.name),
                    date, release.tracksCount)
            cell.set_property('markup', markup)
        self.pack_start(render)
        self.set_cell_data_func(render, celldata)

class ReleaseEventComboBox(gtk.HBox):
    """A ComboBox for picking a release event."""

    def __init__(self):
        super(ReleaseEventComboBox, self).__init__()
        self.model = gtk.ListStore(object, str)
        self.combo = gtk.ComboBox(self.model)
        render = gtk.CellRendererText()
        self.combo.pack_start(render)
        self.combo.set_attributes(render, markup=1)
        self.combo.set_sensitive(False)
        self.label = gtk.Label("_Release:")
        self.label.set_use_underline(True)
        self.label.set_mnemonic_widget(self.combo)
        self.pack_start(self.label, expand=False)
        self.pack_start(self.combo)

    def update(self, release):
        self.model.clear()
        events = release.getReleaseEvents()
        # The catalog number is the most important of these fields, as it's
        # the source for the 'labelid' tag, which we'll use until MB NGS is
        # up and running to deal with multi-disc albums properly. We sort to
        # find the earliest release with a catalog number.
        events.sort(key=lambda e: (bool(not e.getCatalogNumber()),
                                   e.getDate() or '9999-12-31'))
        for rel_event in events:
            text = '%s %s: <b>%s</b> <i>(%s)</i>' % (
                    rel_event.getDate() or '', rel_event.getLabel() or '',
                    rel_event.getCatalogNumber(),rel_event.getCountry())
            self.model.append( (rel_event, text) )
        if len(events) > 0:
            self.combo.set_active(0)
        self.combo.set_sensitive((len(events) > 0))
        text = ngettext("%d _release:", "%d _releases:", len(events))
        self.label.set_text(text % len(events))
        self.label.set_use_underline(True)

    def get_release_event(self):
        itr = self.combo.get_active_iter()
        if itr:
            return self.model[itr][0]
        else:
            return None

class QueryThread:
    """Daemon thread which does HTTP retries and avoids flooding."""
    def __init__(self):
        self.running = True
        self.queue = []
        thread = threading.Thread(target=self.__run)
        thread.daemon = True
        thread.start()

    def add(self, callback, func, *args, **kwargs):
        """Add a func to be evaluated in a background thread.
        Callback will be called with the result from the main thread."""
        self.queue.append((callback, func, args, kwargs))

    def stop(self):
        """Stop the background thread."""
        self.running = False

    def __run(self):
        while self.running:
            if self.queue:
                callback, func, args, kwargs = self.queue.pop(0)
                try:
                    res = func(*args, **kwargs)
                except:
                    time.sleep(2)
                    try:
                        res = func(*args, **kwargs)
                    except:
                        res = None
                gobject.idle_add(callback, res)
            time.sleep(1)


class SearchWindow(gtk.Dialog):
    def __save(self, widget=None, response=None):
        """Writes values to Song objects."""
        self._qthread.stop()
        if response != gtk.RESPONSE_ACCEPT:
            self.destroy()
            return

        album = self.current_release
        shared = {}

        shared['album'] = album.title
        if config_get('split_disc', True):
            m = re.match(r'(.*) \(disc (.*?)\)$', album.title)
            if m:
                shared['album'] = m.group(1)
                disc = m.group(2).split(': ', 1)
                shared['discnumber'] = disc[0]
                if len(disc) > 1:
                    shared['discsubtitle'] = disc[1]

        relevt = self.release_combo.get_release_event()
        shared['date'] = relevt and relevt.getDate() or ''
        if shared['date'] and config_get('year_only', False):
            shared['date'] = shared['date'].split('-')[0]

        if config_get('labelid', True):
            if relevt and relevt.getCatalogNumber():
                shared['labelid'] = relevt.getCatalogNumber()

        if not album.isSingleArtistRelease():
            if (config_get('albumartist', True)
                and extractUuid(album.artist.id) != VARIOUS_ARTISTS_ARTISTID):
                shared['albumartist'] = album.artist.name

        if config_get('standard', True):
            shared['musicbrainz_albumartistid'] = extractUuid(album.artist.id)
            shared['musicbrainz_albumid'] = extractUuid(album.id)

        for idx, (song, ) in enumerate(self.result_treeview.model):
            if song is None: continue
            song.update(shared)
            if idx >= len(album.tracks): continue
            track = album.tracks[idx]
            song['title'] = track.title
            song['tracknumber'] = '%d/%d' % (idx+1,
                    max(len(album.tracks), len(self.result_treeview.model)))
            if config_get('standard', True):
                song['musicbrainz_trackid'] = extractUuid(track.id)
            if album.isSingleArtistRelease() or not track.artist:
                song['artist'] = album.artist.name
            else:
                song['artist'] = track.artist.name
                if config_get('standard', True):
                    song['musicbrainz_artistid'] = extractUuid(track.artist.id)
            if config_get('split_feat', False):
                feats = re.findall(r' \(feat\. (.*?)\)', track.title)
                if feats:
                    feat = []
                    for value in feats:
                        values = value.split(', ')
                        if len(values) > 1:
                            values += values.pop().split(' & ')
                        feat += values
                    song['performer'] = '\n'.join(feat)
                    song['title'] = re.sub(r' \(feat\. .*?\)', '', track.title)

        self.destroy()

    def __do_query(self, *args):
        """Search for album using the query text."""
        query = self.search_query.get_text()
        if not query:
            self.result_label.set_markup("<b>Please enter a query.</b>")
            self.search_button.set_sensitive(True)
            return
        self.result_label.set_markup("<i>Searching...</i>")
        filt = ws.ReleaseFilter(query=query)
        self._qthread.add(self.__process_results,
                         self._query.getReleases, filt)

    def __process_results(self, results):
        """Callback for search query completion."""
        self._resultlist.clear()
        self.search_button.set_sensitive(True)
        if results is None:
            self.result_label.set_text("Error encountered. Please retry.")
            self.search_button.set_sensitive(True)
            return
        for release in map(lambda r: r.release, results):
            self._resultlist.append((release, ))
        if len(results) > 0 and self.result_combo.get_active() == -1:
            self.result_label.set_markup("<i>Loading result...</i>")
            self.result_combo.set_active(0)
        else:
            self.result_label.set_markup("No results found.")

    def __result_changed(self, combo):
        """Called when a release is chosen from the result combo."""
        idx = combo.get_active()
        if idx == -1: return
        rel_id = self._resultlist[idx][0].id
        if rel_id in self._releasecache:
            self.__update_results(self._releasecache[rel_id])
        else:
            self.result_label.set_markup("<i>Loading result...</i>")
            inc = ws.ReleaseIncludes(
                    artist=True, releaseEvents=True, tracks=True)
            self._qthread.add(self.__update_result,
                    self._query.getReleaseById, rel_id, inc)

    def __update_result(self, release):
        """Callback for release detail download from result combo."""
        num_results = len(self._resultlist)
        text = ngettext("Found %d result.", "Found %d results.", num_results)
        self.result_label.set_text(text % num_results)
        self._releasecache.setdefault(extractUuid(release.id), release)
        self.result_treeview.update_remote_album(release.tracks)
        self.current_release = release
        self.release_combo.update(release)
        self.get_action_area().get_children()[1].set_sensitive(True)

    def __init__(self, album, cache):
        self.album = album

        self._query = ws.Query()
        self._resultlist = gtk.ListStore(gobject.TYPE_PYOBJECT)
        self._releasecache = cache
        self._qthread = QueryThread()
        self.current_release = None

        super(SearchWindow, self).__init__("MusicBrainz lookup", buttons=(
                    gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                    gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))
        self.set_default_size(650, 500)
        self.set_border_width(5)

        vb = gtk.VBox()
        vb.set_spacing(8)

        hb = gtk.HBox()
        hb.set_spacing(8)
        sq = self.search_query = gtk.Entry()
        sq.connect('activate', self.__do_query)

        alb = '"%s"' % album[0].comma("album").replace('"', '')
        art = get_artist(album)
        if art:
            alb = '%s AND artist:"%s"' % (alb, art.replace('"', ''))
        sq.set_text('%s AND tracks:%d' %
                (alb, get_trackcount(album)) )

        lbl = gtk.Label("_Query:")
        lbl.set_use_underline(True)
        lbl.set_mnemonic_widget(sq)
        stb = self.search_button = gtk.Button('S_earch')
        stb.connect('clicked', self.__do_query)
        hb.pack_start(lbl, expand=False)
        hb.pack_start(sq)
        hb.pack_start(stb, expand=False)
        vb.pack_start(hb, expand=False)

        self.result_combo = ResultComboBox(self._resultlist)
        self.result_combo.connect('changed', self.__result_changed)
        vb.pack_start(self.result_combo, expand=False)

        rhb = gtk.HBox()
        rl = gtk.Label()
        rl.set_markup("Results <i>(drag to reorder)</i>")
        rl.set_alignment(0, 0.5)
        rhb.pack_start(rl, expand=False)
        rl = self.result_label = gtk.Label("")
        rhb.pack_end(rl, expand=False)
        vb.pack_start(rhb, expand=False)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        rtv = self.result_treeview = ResultTreeView(self.album)
        rtv.set_border_width(8)
        sw.add(rtv)
        vb.pack_start(sw)

        hb = gtk.HBox()
        hb.set_spacing(8)
        self.release_combo = ReleaseEventComboBox()
        vb.pack_start(self.release_combo, expand=False)

        self.get_content_area().pack_start(vb)
        self.connect('response', self.__save)

        stb.emit('clicked')
        self.show_all()


class MyBrainz(SongsMenuPlugin):
    PLUGIN_ID = "MusicBrainz lookup"
    PLUGIN_NAME = "MusicBrainz Lookup"
    PLUGIN_ICON = gtk.STOCK_CDROM
    PLUGIN_DESC = 'Retag an album based on a MusicBrainz search.'
    PLUGIN_VERSION = '0.5'

    cache = {}

    def plugin_albums(self, albums):
        for album in albums:
            discs = {}
            for song in album:
                discnum = int(song.get('discnumber', '1').split('/')[0])
                discs.setdefault(discnum, []).append(song)
            for disc in discs.values():
                s = SearchWindow(disc, self.cache).run()

    @classmethod
    def PluginPreferences(self, win):
        items = [
            ('split_disc', 'Split _disc from album', True),
            ('split_feat', 'Split _featured performers from track', False),
            ('year_only', 'Only use year for "date" tag', False),
            ('albumartist', 'Write "_albumartist" when needed', True),
            ('standard', 'Write _standard MusicBrainz tags', True),
            ('labelid', 'Write _labelid tag (fixes multi-disc albums)', True),
        ]

        vb = gtk.VBox()
        vb.set_spacing(8)

        for key, label, default in items:
            ccb = ConfigCheckButton(label, 'plugins', 'brainz_' + key)
            ccb.set_active(config_get(key, default))
            vb.pack_start(ccb)

        return vb


