# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import datetime
from urllib.parse import urlencode

from gi.repository import GObject, Gio, Soup

from quodlibet import util, config
from quodlibet.util import website
from quodlibet.util.dprint import print_w, print_d
from quodlibet.util.http import download_json, download
from quodlibet.compat import iteritems, text_type

from .library import SoundcloudFile
from .util import json_callback, Wrapper, sanitise_tag, DEFAULT_BITRATE, EPOCH


class RestApi(GObject.Object):
    """Semi-generic REST API client, using libsoup / `http.py`"""

    def __init__(self, root):
        super(RestApi, self).__init__()
        self._cancellable = Gio.Cancellable.new()
        self.root = root

    def _default_params(self):
        return {}

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
        if not isinstance(post_body, bytes):
            post_body = post_body.encode("ascii")
        msg.set_request('application/x-www-form-urlencoded',
                        Soup.MemoryUse.COPY, post_body)
        download_json(msg, self._cancellable, callback, None)

    def _put(self, path, callback, **kwargs):
        args = self._default_params()
        args.update(kwargs)
        msg = Soup.Message.new('PUT', self._url(path))
        body = urlencode(args)
        if not isinstance(body, bytes):
            body = body.encode("ascii")
        msg.set_request('application/x-www-form-urlencoded',
                        Soup.MemoryUse.COPY, body)
        download_json(msg, self._cancellable, callback, None)

    def _delete(self, path, callback, **kwargs):
        args = self._default_params()
        args.update(kwargs)
        # Turns out the SC API doesn't mind body arguments for DELETEs,
        # and as it's neater and slightly more secure, let's do that.
        body = urlencode(args)
        if not isinstance(body, bytes):
            body = body.encode("ascii")
        msg = Soup.Message.new('DELETE', self._url(path))
        msg.set_request('application/x-www-form-urlencoded',
                        Soup.MemoryUse.COPY, body)
        download(msg, self._cancellable, callback, None, try_decode=True)

    def _url(self, path, args=None):
        path = "%s%s" % (self.root, path)
        return "%s?%s" % (path, urlencode(args)) if args else path


class SoundcloudApiClient(RestApi):
    __CLIENT_SECRET = 'ca2b69301bd1f73985a9b47224a2a239'
    __CLIENT_ID = '5acc74891941cfc73ec8ee2504be6617'
    API_ROOT = "https://api.soundcloud.com"
    REDIRECT_URI = 'https://quodlibet.github.io/callbacks/soundcloud.html'
    PAGE_SIZE = 150
    MIN_DURATION_SECS = 120
    COUNT_TAGS = {'%s_count' % t
                  for t in ('playback', 'download', 'likes', 'favoritings',
                            'download', 'comments')}

    __gsignals__ = {
        'fetch-success': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'fetch-failure': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'songs-received': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'comments-received': (GObject.SignalFlags.RUN_LAST, None,
                              (int, object,)),
        'authenticated': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self):
        print_d("Starting Soundcloud API...")
        super(SoundcloudApiClient, self).__init__(self.API_ROOT)
        self.access_token = config.get("browsers", "soundcloud_token", None)
        self.online = bool(self.access_token)
        self.user_id = config.get("browsers", "soundcloud_user_id", None)
        if not self.user_id:
            self._get_me()
        self.username = None

    def _default_params(self):
        params = {'client_id': self.__CLIENT_ID}
        if self.access_token:
            params["oauth_token"] = self.access_token
        return params

    def authenticate_user(self):
        # create client object with app credentials
        if self.access_token:
            print_d("Ignoring saved Soundcloud token...")
        # redirect user to authorize URL
        website(self._authorize_url)

    def log_out(self):
        print_d("Destroying access token...")
        self.access_token = None
        self.save_auth()
        self.online = False

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
        self.save_auth()
        self.online = True
        self._get_me()

    def _get_me(self):
        self._get('/me', self._receive_me)

    @json_callback
    def _receive_me(self, json):
        self.username = json['username']
        self.user_id = json['id']
        self.emit('authenticated', Wrapper(json))

    def get_tracks(self, params):
        merged = {
            "q": "",
            "limit": self.PAGE_SIZE,
            "duration[from]": self.MIN_DURATION_SECS * 1000,
        }
        for k, v in iteritems(params):
            delim = " " if k == 'q' else ","
            merged[k] = delim.join(list(v))
        print_d("Getting tracks: params=%s" % merged)
        self._get('/tracks', self._on_track_data, **merged)

    @json_callback
    def _on_track_data(self, json):
        songs = list(filter(None, [self._audiofile_for(r) for r in json]))
        self.emit('songs-received', songs)

    def get_favorites(self):
        self._get('/me/favorites', self._on_track_data, limit=self.PAGE_SIZE)

    def get_my_tracks(self):
        self._get('/me/tracks', self._on_track_data, limit=self.PAGE_SIZE)

    def get_comments(self, track_id):
        self._get('/tracks/%s/comments' % track_id, self._receive_comments,
                  limit=200)

    @json_callback
    def _receive_comments(self, json):
        print_d("Got comments: %s" % json)
        if json and len(json):
            # Should all be the same track...
            track_id = json[0]["track_id"]
            self.emit('comments-received', track_id, json)

    def save_auth(self):
        config.set("browsers", "soundcloud_token", self.access_token or "")
        config.set("browsers", "soundcloud_user_id", self.user_id or "")

    def put_favorite(self, track_id):
        print_d("Saving track %s as favorite" % track_id)
        url = '/me/favorites/%s' % track_id
        self._put(url, self._on_favorited)

    def remove_favorite(self, track_id):
        print_d("Deleting favorite for %s" % track_id)
        url = '/me/favorites/%s' % track_id
        self._delete(url, self._on_favorited)

    @json_callback
    def _on_favorited(self, json):
        print_d("Successfully updated favorite: %s" % json)

    def _audiofile_for(self, response):
        r = Wrapper(response)
        d = r.data
        dl = d.get("downloadable", False) and d.get("download_url", None)
        try:
            url = dl or r.stream_url
        except AttributeError as e:
            print_w("Unusable result (%s) from SC: %s" % (e, d))
            return None
        uri = SoundcloudApiClient._add_secret(url)
        song = SoundcloudFile(uri=uri,
                              track_id=r.id,
                              favorite=d.get("user_favorite", False),
                              client=self)

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

        def put_counts(tags):
            for tag in tags:
                try:
                    song["~#%s" % tag] = int(r[tag])
                except KeyError:
                    pass

        try:
            song.update(title=r.title,
                        artist=r.user["username"],
                        soundcloud_user_id=text_type(r.user_id),
                        website=r.permalink_url,
                        genre=u"\n".join(r.genre and r.genre.split(",") or []))
            if dl:
                song.update(format=r.original_format)
                song["~#bitrate"] = r.original_content_size * 8 / r.duration
            else:
                song["~#bitrate"] = DEFAULT_BITRATE
            if r.description:
                song["comment"] = sanitise_tag(r.description)
            song["~#length"] = int(r.duration) / 1000
            art_url = r.artwork_url
            if art_url:
                song["artwork_url"] = (
                    art_url.replace("-large.", "-t500x500."))
            put_time("~#mtime", r, "last_modified")
            put_date("date", r, "created_at")
            put_counts(self.COUNT_TAGS)
            plays = d.get("user_playback_count", 0)
            if plays:
                song["~#playcount"] = plays
            # print_d("Got song: %s" % song)
        except Exception as e:
            print_w("Couldn't parse a song from %s (%r). "
                    "Had these tags:\n  %s" % (r, e, song.keys()))
        return song

    @classmethod
    def _add_secret(cls, stream_url):
        return "%s?client_id=%s" % (stream_url, cls.__CLIENT_ID)

    @util.cached_property
    def _authorize_url(self):
        url = '%s/connect' % (self.API_ROOT,)
        options = {
            'scope': 'non-expiring',
            'client_id': self.__CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': self.REDIRECT_URI

        }
        return '%s?%s' % (url, urlencode(options))
