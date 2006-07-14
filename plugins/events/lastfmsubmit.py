# A Last.fm client plugin for Quod Libet. Unlike QLScrobbler, this uses
# the Python lastfm module by Decklin Foster.
# Copyright 2005-2006 Joshua Kwan, Joe Wreschnig
# Licensed under the terms of the GNU GPL v2.

import time

import gobject
import gtk

import lastfm

import config
import player
import parse

from plugins.events import EventPlugin
from qltk.entry import ValidatingEntry

class QLLastfm(EventPlugin):
    PLUGIN_NAME = "Last.fm Submission"
    PLUGIN_DESC = "Submit songs to Last.fm via lastfmsubmitd."
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.2"

    __exclude = ""
    __song = None
    __timeout_id = -1
    __log = lastfm.logger('quodlibet')

    def __init__(self):
        try: self.__exclude = config.get("plugins", "scrobbler_exclude")
        except: pass

    def unprepare(self):
        if self.__timeout_id > 0:
            gobject.source_remove(self.__timeout_id)
        self.__song = None
        self.__timeout_id = -1

    def prepare(self):
        if self.__song is None: return

        if self.__timeout_id > 0:
            gobject.source_remove(self.__timeout_id)
            self.__timeout_id = -1

        # Protocol stipulations:
        #  * submit 240 seconds in or at 50%, whichever comes first
        delay = int(min(self.__song["~#length"] / 2, 240))

        progress = int(player.playlist.get_position() // 1000)
        delay -= progress
        self.__timeout_id = gobject.timeout_add(delay * 1000, self.submit_song)

    def plugin_on_removed(self, songs):
        try:
            if self.__song in songs: self.unprepare()
        except:
            if self.__song is songs: self.unprepare()

    def PluginPreferences(self, parent):
        def changed(entry):
            config.set("plugins", "scrobbler_exclude", entry.get_text())
            self.__exclude = entry.get_text().decode('utf-8')

        lv = gtk.Label(_("Exclude:"))
        ve = ValidatingEntry(parse.Query.is_valid_color)
        ve.set_text(self.__exclude)
        hb = gtk.HBox(spacing=12)
        hb.pack_start(lv, expand=False)
        hb.pack_start(ve, expand=True)
        return hb

    def plugin_on_song_ended(self, song, stopped):
        self.unprepare()

    def plugin_on_song_started(self, song):
        if song is None:
            self.unprepare()
            return

        # Protocol stipulation:
        #  * don't submit when length < 00:30
        #  * don't submit if artist and title are not available
        if song["~#length"] < 30: return
        elif 'title' not in song: return
        elif not song("~artist~composer~performer"): return

        # Check to see if this song is not something we'd like to submit
        # e.g. "Hit Me Baby One More Time"
        if self.__exclude != "" and parse.Query(self.__exclude).search(song):
            print "Not submitting: %s - %s" % (song["artist"], song["title"])
            return

        self.__song = song
        if not player.playlist.paused:
            self.prepare()

    def plugin_on_paused(self):
        if self.__song and self.__timeout_id > 0:
            gobject.source_remove(self.__timeout_id)
            self.__timeout_id = -1

    def plugin_on_unpaused(self):
        self.prepare()

    def plugin_on_seek(self, song, msec):
        self.unprepare()

        # Except seeking to 0 is okay, so re-queue the submission
        if msec == 0:
            self.__song = song
            self.prepare()

    def submit_song(self):
        data = {
            "title": self.__song("title"),
            "length": self.__song["~#length"],
            "mbid": self.__song.get("musicbrainz_trackid"),
            "time": time.gmtime(),
            "album": self.__song.get("album"),
            "artist":
            self.__song.get("artist",
                            self.__song.get("composer",
                                            self.__song.get("performer"))),
            }
        self.unprepare()

        for key in data.keys():
            if not data[key]: del(data[key])
        try:
            lastfm.submit([data])
            self.__log.info("Sent %s", lastfm.repr(data))
        except IOError, e: self.__log.error("Error: %s" % e)
