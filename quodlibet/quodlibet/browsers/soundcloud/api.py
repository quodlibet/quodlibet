# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gi
from datetime import datetime
from gi.repository import GObject, Gio
from urllib import urlencode

from quodlibet import print_d, util, config
from quodlibet.browsers.soundcloud.util import EPOCH, DEFAULT_BITRATE, \
    Wrapper, json_callback
from quodlibet.formats.remote import RemoteFile
from quodlibet.util import website
from quodlibet.util.dprint import print_w
from quodlibet.util.http import download_json

try:
    gi.require_version("Soup", "2.4")
except ValueError as e:
    raise ImportError(e)
from gi.repository import Soup


class SoundcloudApiClient(GObject.Object):
    __CLIENT_SECRET = 'ca2b69301bd1f73985a9b47224a2a239'
    __CLIENT_ID = '5acc74891941cfc73ec8ee2504be6617'
    SOUNDCLOUD_API_HOST = "https://api.soundcloud.com"
    REDIRECT_URI = 'quodlibet://soundcloud/callback'

    __gsignals__ = {
        'fetch-success': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'fetch-failure': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'songs-received': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'authenticated': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self, token=None):
        super(SoundcloudApiClient, self).__init__()
        print_d("Starting Soundcloud API...")
        self.online = False
        self.username = None
        self.access_token = token
        self._cancellable = Gio.Cancellable.new()

    def authenticate_user(self):
        # create client object with app credentials
        if self.access_token:
            print_d("Using saved Soundcloud token...")
        else:
            # redirect user to authorize URL
            website(self.authorize_url)

    def get_token(self, code):
        print_d("Getting access token...")
        options = {
            'grant_type': 'authorization_code',
            'redirect_uri': self.REDIRECT_URI,
            'client_id': self.__CLIENT_ID,
            'client_secret': self.__CLIENT_SECRET,
            'code': code,
        }
        self._post('/oauth2/token', self._receive_token, **options)

    @json_callback
    def _receive_token(self, json):
        self.access_token = json['access_token']
        print_d("Got an access token: %s" % self.access_token)
        self.save_token()
        self.online = True
        self._get('/me', self._receive_me)

    @json_callback
    def _receive_me(self, json):
        self.username = json['username']
        self.emit('authenticated', Wrapper(json))

    def get_tracks(self, query):
        params = {
            "q": query,
            "limit": 100,
            "duration[from]": 100 * 1000,
            "duration[to]": 10000 * 1000
        }
        print_d("Getting tracks: params=%s" % params)
        self._get('/tracks', self._on_track_data, **params)

    def _get(self, path, callback, **kwargs):
        args = self._default_params()
        args.update(kwargs)
        msg = Soup.Message.new('GET', self._url(path, args))
        download_json(msg, self._cancellable, callback, None)

    def _post(self, path, callback, **kwargs):
        args = self._default_params()
        args.update(kwargs)
        msg = Soup.Message.new('POST', self._url(path))
        post_body = urlencode(args)
        msg.set_request('application/x-www-form-urlencoded',
                        Soup.MemoryUse.COPY, post_body)
        download_json(msg, self._cancellable, callback, None)

    def _default_params(self):
        params = {'client_id': self.__CLIENT_ID}
        if self.access_token:
            params["oauth_token"] = self.access_token
        return params

    def _url(self, path, args=None):
        base = "%s%s" % (self.SOUNDCLOUD_API_HOST, path)
        return "%s?%s" % (base, urlencode(args)) if args else base

    @json_callback
    def _on_track_data(self, json):
        songs = [self.audiofile_for(r) for r in json]
        self.emit('songs-received', songs)

    @classmethod
    def audiofile_for(cls, response):
        r = Wrapper(response)
        d = r.data
        dl = d.get("downloadable", False) and d.get("download_url", None)
        uri = SoundcloudApiClient.add_secret(dl or r.stream_url)
        song = RemoteFile(uri=uri)

        def get_utc_date(s):
            parts = s.split()
            dt = datetime.strptime(" ".join(parts[:-1]), "%Y/%m/%d %H:%M:%S")
            return int((dt - EPOCH).total_seconds())

        def put_time(tag, r, attr):
            try:
                song[tag] = get_utc_date(r[attr])
            except KeyError:
                pass

        def put_date(tag, r, attr):
            try:
                parts = r[attr].split()
                dt = datetime.strptime(" ".join(parts[:-1]),
                                       "%Y/%m/%d %H:%M:%S")
                song[tag] = dt.strftime("%Y-%m-%d")
            except KeyError:
                pass

        def put_counts(*args):
            for name in args:
                tag = "%s_count" % name
                try:
                    song["~#%s" % tag] = int(r[tag])
                except KeyError:
                    pass

        try:
            song.update(title=r.title,
                        artist=r.user["username"],
                        comment=r.description,
                        website=r.permalink_url,
                        genre="\n".join(r.genre and r.genre.split(",") or []))
            if dl:
                song.update(format=r.original_format)
                song["~#bitrate"] = r.original_content_size * 8 / r.duration
            else:
                song["~#bitrate"] = DEFAULT_BITRATE
            song["~#length"] = int(r.duration) / 1000
            song["soundcloud_track_id"] = r.id
            art_url = r.artwork_url
            if art_url:
                song["artwork_url"] = (
                    art_url.replace("-large.", "-t500x500."))
            put_time("~#mtime", r, "last_modified")
            put_date("date", r, "created_at")
            if d.get("user_favorite", False):
                song["~#rating"] = 1.0
            put_counts("playback", "download", "favoritings", "likes")
            plays = d.get("user_playback_count", 0)
            if plays:
                song["~#playcount"] = plays
            print_d("Got song: %s" % song)
        except Exception as e:
            print_w("Couldn't parse a song from %s (%r). "
                    "Had these tags:\n  %s" % (r, e, song.keys()))
        return song

    @classmethod
    def add_secret(cls, stream_url):
        return "%s?client_id=%s" % (stream_url, cls.__CLIENT_ID)

    def save_token(self):
        if self.access_token:
            config.set("browsers", "soundcloud_token", self.access_token)

    @util.cached_property
    def authorize_url(self):
        url = '%s/connect' % (self.SOUNDCLOUD_API_HOST,)
        options = {
            'scope': 'non-expiring',
            'client_id': self.__CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': self.REDIRECT_URI

        }
        return '%s?%s' % (url, urlencode(options))
