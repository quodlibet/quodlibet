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

import config
import const

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

class PlaylistPlayer(gtk.Object):
    """Interfaces between a QL PlaylistModel and a GSt playbin.

    Attributes:
    paused -- True or False, set to pause/unpause the player
    volume -- current volume, 0.0 to 1.0

    song -- current song, or None if not playing
    info -- current stream information, or None if not playing. This is
            usually the same as song, unless the user is listening to
            a stream with multiple songs in it.

    If you're going to show things, use .info. If you're going to
    change things, use .song.
    """

    __paused = False
    song = None
    info = None
    # Replay Gain profiles are a list of values to be tried in order;
    # Three things can set them: play order, browser, and a default.
    replaygain_profiles = [None, None, ["none"]]
    __length = 1
    __volume = 1.0

    __gsignals__ = {
        'song-started':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'song-ended':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, bool)),
        'seek':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, int)),
        'paused': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'unpaused': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'error': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str, bool)),
        }

    __gproperties__ = {
        'volume': (float, 'player volume', 'the volume of the player',
                   0.0, 1.0, 1.0, gobject.PARAM_READWRITE)
        }

    def __init__(self, sinkname, librarian=None):
        super(PlaylistPlayer, self).__init__()
        device, sinkname = GStreamerSink(sinkname)
        self.name = sinkname
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
            self.__source.next_ended()
            self.__end(False)
        elif message.type == gst.MESSAGE_TAG:
            self.__tag(message.parse_tag(), librarian)
        elif message.type == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            err = str(err).decode(const.ENCODING, 'replace')
            self.error(err, True)
        return True

    def do_song_started(self, song):
        # Reset Replay Gain levels based on the new song.
        self.volume = self.volume
    def do_song_ended(self, song, stopped):
        self.volume = self.volume

    def do_get_property(self, property):
        if property.name == 'volume':
            return self.__volume
        else: raise AttributeError

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self.__volume = v
            if self.song is None:
                self.bin.set_property('volume', v)
            else:
                if config.getboolean("player", "replaygain"):
                    profiles = filter(None, self.replaygain_profiles)[0]
                    v = max(0.0, min(4.0, v * self.song.replay_gain(profiles)))
                self.bin.set_property('volume', v)
        else:
            raise AttributeError

    def setup(self, source, song):
        """Connect to a PlaylistModel, and load a song."""
        self.__source = source
        self.go_to(song)

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        if self.bin.get_property('uri'):
            try: p = self.bin.query_position(gst.FORMAT_TIME)[0]
            except gst.QueryError: p = 0
            p //= gst.MSECOND
            return p
        else: return 0
        
    def __set_paused(self, paused):
        if paused != self.__paused:
            self.__paused = paused
            if self.song:
                self.emit((paused and 'paused') or 'unpaused')
                if self.__paused:
                   if not self.song.is_file:
                       self.bin.set_state(gst.STATE_NULL)
                   else: self.bin.set_state(gst.STATE_PAUSED)
                else: self.bin.set_state(gst.STATE_PLAYING)
            elif paused is True:
                # Something wants us to pause between songs, or when
                # we've got no song playing (probably StopAfterMenu).
                self.emit('paused')
    def __get_paused(self): return self.__paused
    paused = property(__get_paused, __set_paused)

    def __set_volume(self, v):
        self.props.volume = min(1.0, max(0.0, v))
    volume = property(lambda s: s.__volume, __set_volume)

    def error(self, message, lock):
        self.bin.set_property('uri', '')
        self.bin.set_state(gst.STATE_NULL)
        if not self.song or not self.song.get("~error"):
            if self.song:
                self.song["~error"] = "1"
            self.paused = True
            self.emit('error', message, lock)
            self.emit('song-started', None)
            self.song = self.info = None
        else:
            self.next()

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""
        if self.bin.get_property('uri'):
            pos = max(0, int(pos))
            if pos >= self.__length:
                self.paused = True
                pos = self.__length

            gst_time = pos * gst.MSECOND
            event = gst.event_new_seek(
                1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH,
                gst.SEEK_TYPE_SET, gst_time, gst.SEEK_TYPE_NONE, 0)
            if self.bin.send_event(event):
                self.emit('seek', self.song, pos)

    def remove(self, song):
        if self.song is song:
            self.__end(False)

    def __end(self, stopped):
        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        song = self.song
        self.song = self.info = None
        self.emit('song-ended', song, stopped)

        # Then, set up the next song.
        self.song = self.info = self.__source.current
        self.emit('song-started', self.song)

        if self.song is not None:
            # Changing the URI in a playbin requires "resetting" it.
            if not self.bin.set_state(gst.STATE_NULL): return
            self.bin.set_property('uri', self.song("~uri"))
            self.__length = self.song["~#length"] * 1000
            if self.__paused: self.bin.set_state(gst.STATE_PAUSED)
            else: self.bin.set_state(gst.STATE_PLAYING)
        else:
            
            self.paused = True
            self.bin.set_state(gst.STATE_NULL)
            self.bin.set_property('uri', '')

    def __tag(self, tags, librarian):
        if self.song and self.song.multisong:
            self.__fill_stream(tags, librarian)
        elif self.song and self.song.fill_metadata:
            pass

    def __fill_stream(self, tags, librarian):
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

    def reset(self):
        self.__source.reset()
        if self.__source.current is not None:
            self.__end(True)
            if self.song: self.paused = False

    def next(self):
        self.__source.next()
        self.__end(True)
        if self.song: self.paused = False

    def previous(self):
        self.__source.previous()
        self.__end(True)
        if self.song: self.paused = False

    def go_to(self, song):
        self.__source.go_to(song)
        self.__end(True)

global playlist
playlist = None

def init(pipeline, librarian):
    gst.debug_set_default_threshold(gst.LEVEL_ERROR)
    if gst.element_make_from_uri(gst.URI_SRC, "file://", ""):
        global playlist
        playlist = PlaylistPlayer(pipeline or "gconfaudiosink", librarian)
        return playlist
    else: raise NoSourceError
