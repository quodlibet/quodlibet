# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject
import gst
import gtk

from quodlibet import config
from quodlibet import const

from quodlibet.util import fver
from quodlibet.player._base import BasePlayer

class NoSinkError(ValueError): pass
class NoSourceError(ValueError): pass

def GStreamerSink(pipeline):
    """Try to create a GStreamer pipeline:
    * Try making the pipeline (defaulting to gconfaudiosink).
    * If it fails, fall back to autoaudiosink.
    * If that fails, complain loudly."""

    if pipeline == "gconf": pipeline = "gconfaudiosink"
    try: pipe = gst.parse_launch(pipeline)
    except gobject.GError, err:
        if pipeline != "autoaudiosink":
            try: pipe = gst.parse_launch("autoaudiosink")
            except gobject.GError: pipe = None
            else: pipeline = "autoaudiosink"
        else: pipe = None
    if pipe: return pipe, pipeline
    else: raise NoSinkError(pipeline)

class GStreamerPlayer(BasePlayer):
    __gproperties__ = BasePlayer._gproperties_
    __gsignals__ = BasePlayer._gsignals_

    def __init__(self, sinkname, librarian=None):
        super(GStreamerPlayer, self).__init__()
        device, sinkname = GStreamerSink(sinkname)
        self.name = sinkname
        self.version_info = "GStreamer: %s / PyGSt: %s" % (
            fver(gst.version()), fver(gst.pygst_version))
        self.bin = gst.element_factory_make('playbin')
        self.bin.set_property('video-sink', None)
        self.bin.set_property('audio-sink', device)
        bus = self.bin.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.__message, librarian)
        self.connect_object('destroy', self.bin.set_state, gst.STATE_NULL)
        self.paused = True

    def __message(self, bus, message, librarian):
        if message.type == gst.MESSAGE_EOS:
            self._source.next_ended()
            self._end(False)
        elif message.type == gst.MESSAGE_TAG:
            self.__tag(message.parse_tag(), librarian)
        elif message.type == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            err = str(err).decode(const.ENCODING, 'replace')
            self.error(err, True)
        return True

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self._volume = v
            if self.song is None:
                self.bin.set_property('volume', v)
            else:
                if config.getboolean("player", "replaygain"):
                    profiles = filter(None, self.replaygain_profiles)[0]
                    v = max(0.0, min(4.0, v * self.song.replay_gain(profiles)))
                self.bin.set_property('volume', v)
        else:
            raise AttributeError

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        if self.bin.get_property('uri'):
            try: p = self.bin.query_position(gst.FORMAT_TIME)[0]
            except gst.QueryError: p = 0
            p //= gst.MSECOND
            return p
        else: return 0
        
    def _set_paused(self, paused):
        if paused != self._paused:
            self._paused = paused
            if self.song:
                self.emit((paused and 'paused') or 'unpaused')
                if self._paused:
                   if not self.song.is_file:
                       self.bin.set_state(gst.STATE_NULL)
                   else: self.bin.set_state(gst.STATE_PAUSED)
                else: self.bin.set_state(gst.STATE_PLAYING)
            elif paused is True:
                # Something wants us to pause between songs, or when
                # we've got no song playing (probably StopAfterMenu).
                self.emit('paused')
    def _get_paused(self): return self._paused
    paused = property(_get_paused, _set_paused)

    def error(self, message, lock):
        self.bin.set_property('uri', '')
        self.bin.set_state(gst.STATE_NULL)
        self.emit('error', self.song, message, lock)
        if not self.paused:
            self.next()

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""
        if self.bin.get_property('uri'):
            pos = max(0, int(pos))
            if pos >= self._length:
                self.paused = True
                pos = self._length

            gst_time = pos * gst.MSECOND
            event = gst.event_new_seek(
                1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH,
                gst.SEEK_TYPE_SET, gst_time, gst.SEEK_TYPE_NONE, 0)
            if self.bin.send_event(event):
                self.emit('seek', self.song, pos)

    def _end(self, stopped):
        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        song = self.song
        self.song = self.info = None
        self.emit('song-ended', song, stopped)

        # Then, set up the next song.
        self.song = self.info = self._source.current
        self.emit('song-started', self.song)

        if self.song is not None:
            # Changing the URI in a playbin requires "resetting" it.
            if not self.bin.set_state(gst.STATE_NULL): return
            self.bin.set_property('uri', self.song("~uri"))
            self._length = self.song["~#length"] * 1000
            if self._paused: self.bin.set_state(gst.STATE_PAUSED)
            else: self.bin.set_state(gst.STATE_PLAYING)
        else:
            
            self.paused = True
            self.bin.set_state(gst.STATE_NULL)
            self.bin.set_property('uri', '')

    def __tag(self, tags, librarian):
        if self.song and self.song.multisong:
            self._fill_stream(tags, librarian)
        elif self.song and self.song.fill_metadata:
            pass

    def _fill_stream(self, tags, librarian):
        changed = False
        started = False
        if self.info is self.song:
            self.info = type(self.song)(self.song["~filename"])
            self.info.multisong = False

        for k in tags.keys():
            value = str(tags[k]).strip()
            if not value: continue
            if k == "bitrate":
                try: bitrate = int(value)
                except (ValueError, TypeError): pass
                else:
                    if bitrate != self.song.get("~#bitrate"):
                        changed = True
                        self.song["~#bitrate"] = bitrate
                        self.info["~#bitrate"] = bitrate
            elif k == "duration":
                try: length = int(long(value) / gst.SECOND)
                except (ValueError, TypeError): pass
                else:
                    if length != self.song.get("~#length"):
                        changed = True
                        self.info["~#length"] = length
            elif k in ["emphasis", "mode", "layer"]:
                continue
            elif isinstance(value, basestring):
                value = unicode(value, errors='replace')
                k = {"track-number": "tracknumber",
                     "location": "website"}.get(k, k)
                if self.info.get(k) == value:
                    continue
                elif k == "title":
                    self.info[k] = value
                    started = True
                else:
                    self.song[k] = self.info[k] = value
                changed = True

        if started:
            self.emit('song-started', self.info)
        elif changed and librarian is not None:
            librarian.changed([self.song])

_mimetypes = None

def _load_mimetypes():
    global _mimetypes
    _mimetypes = set()
    def flt(f):
        klass = f.get_klass()
        return 'Decoder' in klass or 'Demux' in klass or 'Parse' in klass
    factories = filter(flt, gst.registry_get_default().get_feature_list(gst.TYPE_ELEMENT_FACTORY))
    for factory in factories:
        caps = [t.get_caps() for t in factory.get_static_pad_templates() if t.name_template == 'sink']
        for cap in caps:
            for struct in cap:
                _mimetypes.add(struct.get_name())

def can_play_mime(mime):
    global _mimetypes
    if _mimetypes is None:
        _load_mimetypes()
    return mime in _mimetypes

def can_play_uri(uri):
    return gst.element_make_from_uri(gst.URI_SRC, uri, '') is not None

def init(librarian):
    pipeline = config.get("player", "gst_pipeline") or "gconfaudiosink"
    gst.debug_set_default_threshold(gst.LEVEL_ERROR)
    if gst.element_make_from_uri(
        gst.URI_SRC,
        "file:///Sebastian/Droge/please/choke/on/a/bucket/of/cocks", ""):
        return GStreamerPlayer(pipeline, librarian)
    else: raise NoSourceError
