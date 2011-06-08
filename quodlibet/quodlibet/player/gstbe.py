# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Steven Robertson,
#                     Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gobject
import os

import pygst
pygst.require("0.10")

import gst
try:
    from gst import pbutils
except ImportError:
    pbutils = None

from quodlibet import config
from quodlibet import const
from quodlibet import util

from quodlibet.util import fver
from quodlibet.player import error as PlayerError
from quodlibet.player._base import BasePlayer
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk.notif import Task
from quodlibet.qltk.entry import UndoEntry

USE_PLAYBIN2 = gst.version() >= (0, 10, 24)

def GStreamerSink(pipeline):
    """Try to create a GStreamer pipeline:
    * Try making the pipeline (defaulting to gconfaudiosink or
      autoaudiosink on Windows).
    * If it fails, fall back to autoaudiosink.
    * If that fails, return None

    Returns the pipeline's description and a list of disconnected elements."""

    if not pipeline and not gst.element_factory_find('gconfaudiosink'):
        pipeline = "autoaudiosink"
    elif not pipeline or pipeline == "gconf":
        pipeline = "gconfaudiosink profile=music"

    try: pipe = [gst.parse_launch(element) for element in pipeline.split('!')]
    except gobject.GError, err:
        print_w(_("Invalid GStreamer output pipeline, trying default."))
        try: pipe = [gst.parse_launch("autoaudiosink")]
        except gobject.GError: pipe = None
        else: pipeline = "autoaudiosink"

    if pipe:
        # In case the last element is linkable with a fakesink
        # it is not an audiosink, so we append the default pipeline
        fake = gst.element_factory_make('fakesink')
        try:
            gst.element_link_many(pipe[-1], fake)
        except gst.LinkError: pass
        else:
            gst.element_unlink_many(pipe[-1], fake)
            default, default_text = GStreamerSink("")
            if default:
                return pipe + default, pipeline + " ! "  + default_text
    else:
        print_w(_("Could not create default GStreamer pipeline."))

    return pipe, pipeline

class GStreamerPlayer(BasePlayer):
    __gproperties__ = BasePlayer._gproperties_
    __gsignals__ = BasePlayer._gsignals_

    _paused = True
    _in_gapless_transition = False
    _inhibit_play = False
    _finish_position = -1
    _last_position = 0

    _task = None

    bin = None
    _vol_element = None
    _eq_element = None

    __atf_id = None
    __bus_id = None

    def PlayerPreferences(self):
        e = UndoEntry()
        e.set_tooltip_text(_("The GStreamer output pipeline used for "
                "playback, such as 'alsasink device=default'. "
                "Leave blank for default pipeline."))
        e.set_text(config.get('player', 'gst_pipeline'))
        def changed(entry):
            config.set('player', 'gst_pipeline', entry.get_text())
        e.connect('changed', changed)

        l = gtk.Label(_('_Output pipeline:'))
        l.set_use_underline(True)
        l.set_mnemonic_widget(e)

        def apply_pipeline(*args):
            paused = self.paused
            pos = self.get_position()
            self.__destroy_pipeline()
            self.paused = True
            self.go_to(self.song)
            self.paused = paused
            self.seek(pos)

        b = gtk.Button(stock=gtk.STOCK_APPLY)
        b.connect('clicked', apply_pipeline)

        hb = gtk.HBox(spacing=6)
        hb.pack_start(l, expand=False)
        hb.pack_start(e)
        hb.pack_start(b, expand=False)

        def format_buffer(scale, value):
            # seconds
            return _("%.1f s") % value

        def scale_changed(scale):
            config.set("player", "gst_buffer", scale.get_value())
            if self.bin:
                duration = int(scale.get_value() * 1000) * gst.MSECOND
                self.bin.set_property('buffer-duration', duration)

        duration = config.getfloat("player", "gst_buffer")
        scale = gtk.HScale(gtk.Adjustment(duration, 0.2, 10))
        scale.set_value_pos(gtk.POS_RIGHT)
        scale.set_show_fill_level(True)
        scale.connect('format-value', format_buffer)
        scale.connect('value-changed', scale_changed)

        l = gtk.Label(_('_Buffer duration:'))
        l.set_use_underline(True)
        l.set_mnemonic_widget(scale)

        hb2 = gtk.HBox(spacing=6)
        hb2.pack_start(l, expand=False)
        hb2.pack_start(scale)

        vbox = gtk.VBox(spacing=6)
        vbox.pack_start(hb)
        if USE_PLAYBIN2:
            vbox.pack_start(hb2)

        return vbox

    def __init__(self, librarian=None):
        super(GStreamerPlayer, self).__init__()
        self.version_info = "GStreamer: %s / PyGSt: %s" % (
            fver(gst.version()), fver(gst.pygst_version))
        self._librarian = librarian
        self.connect('destroy', lambda s: self.__destroy_pipeline())

    def __init_pipeline(self):
        """Creates a gstreamer pipeline with the following elements

        For newer gstreamer versions:
            playbin2 -> bin [ <- ghostpad -> queue -> volume -> capsfilter
                -> equalizer -> audioconvert -> user defined elements
                -> gconf/autoaudiosink ]

        For older versions:
            playbin -> bin [ <- ghostpad -> capsfilter -> equalizer
                -> audioconvert -> user defined elements
                -> gconf/autoaudiosink ]
        """
        if self.bin: return True

        # TODO: use the volume property of the sink if available (pulsesink)

        pipeline = config.get("player", "gst_pipeline")
        pipeline, self.name = GStreamerSink(pipeline)
        if not pipeline:
            return False

        if gst.element_factory_find('equalizer-10bands'):
            # The equalizer only operates on 16-bit ints or floats, and
            # will only pass these types through even when inactive.
            # We push floats through to this point, then let the second
            # audioconvert handle pushing to whatever the rest of the
            # pipeline supports. As a bonus, this seems to automatically
            # select the highest-precision format supported by the
            # rest of the chain.
            filt = gst.element_factory_make('capsfilter')
            filt.set_property('caps',
                              gst.caps_from_string('audio/x-raw-float'))
            eq = gst.element_factory_make('equalizer-10bands')
            self._eq_element = eq
            self.update_eq_values()
            conv = gst.element_factory_make('audioconvert')
            pipeline = [filt, eq, conv] + pipeline

        if USE_PLAYBIN2:
            # The output buffer is necessary to run the song-ended and
            # song-started events through QL's signal handlers before the
            # playbin2 hits EOF inside a gapless transition.
            queue = gst.element_factory_make('queue')
            queue.set_property('max-size-time', 500 * gst.MSECOND)

            # The volume element is needed to remove the volume change delay.
            self._vol_element = gst.element_factory_make('volume')
            pipeline = [queue,  self._vol_element] + pipeline

        bufbin = gst.Bin()
        map(bufbin.add, pipeline)
        try:
            gst.element_link_many(*pipeline)
        except gst.LinkError, e:
            print_w(_("Could not link GStreamer pipeline: '%s'") % e)
            self.__destroy_pipeline()
            return False

        # Test to ensure output pipeline can preroll
        bufbin.set_state(gst.STATE_READY)
        result, state, pending = bufbin.get_state()
        bufbin.set_state(gst.STATE_NULL)
        if result == gst.STATE_CHANGE_FAILURE:
            self.__destroy_pipeline()
            return False

        # Make the sink of the first element the sink of the bin
        gpad = gst.GhostPad('sink', pipeline[0].get_pad('sink'))
        bufbin.add_pad(gpad)

        if USE_PLAYBIN2:
            self.bin = gst.element_factory_make('playbin2')
            self.__atf_id = self.bin.connect('about-to-finish',
                self.__about_to_finish)
            duration = config.getfloat("player", "gst_buffer")
            duration = int(duration * 1000) * gst.MSECOND
            self.bin.set_property('buffer-duration', duration)
        else:
            self.bin = gst.element_factory_make('playbin')
            self._vol_element = self.bin

        self.bin.set_property('audio-sink', bufbin)

        # by default playbin will render video -> suppress using fakesink
        fakesink = gst.element_factory_make('fakesink')
        self.bin.set_property('video-sink', fakesink)

        # ReplayGain information gets lost when destroying
        self.volume = self.volume

        bus = self.bin.get_bus()
        bus.add_signal_watch()
        self.__bus_id = bus.connect('message', self.__message, self._librarian)

        return True

    def __destroy_pipeline(self):
        if self._task:
            self._task.finish()
            self._task = None

        self._in_gapless_transition = False
        self._inhibit_play = False
        self._finish_position = -1
        self._last_position = 0

        self._vol_element = None
        self._eq_element = None

        if self.bin is None: return
        self.bin.set_state(gst.STATE_NULL)

        bus = self.bin.get_bus()
        if self.__bus_id:
            bus.disconnect(self.__bus_id)
            bus.remove_signal_watch()

        if self.__atf_id:
            self.bin.disconnect(self.__atf_id)

        self.bin = None

        return True

    def __message(self, bus, message, librarian):
        if message.type == gst.MESSAGE_EOS:
            if not self._in_gapless_transition:
                self._source.next_ended()
            self._end(False)
        elif message.type == gst.MESSAGE_TAG:
            self.__tag(message.parse_tag(), librarian)
        elif message.type == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            err = str(err).decode(const.ENCODING, 'replace')
            self.error(err, True)
        elif message.type == gst.MESSAGE_BUFFERING:
            percent = message.parse_buffering()
            self.__buffering(percent)
        elif message.type == gst.MESSAGE_ELEMENT:
            name = ""
            if hasattr(message.structure, "get_name"):
                name = message.structure.get_name()

            # This gets sent on song change. Because it is not in the docs
            # we can not rely on it. Additionally we check in get_position
            # which should trigger shortly after this.
            if self._in_gapless_transition and \
                name == "playbin2-stream-changed":
                    self._end(False)

            if pbutils and name.startswith('missing-'):
                self.stop()
                detail = pbutils.missing_plugin_message_get_installer_detail(
                    message)
                context = pbutils.InstallPluginsContext()
                pbutils.install_plugins_async([detail], context,
                    lambda *args: gst.update_registry())

        return True

    def __about_to_finish(self, pipeline):
        def check_position(*args):
            # Query the current position until gapless is over
            self.get_position()
            return self._in_gapless_transition

        self._in_gapless_transition = False
        self._finish_position = self.get_position()
        self._in_gapless_transition = True

        # song change is about to happen, check frequently
        gobject.timeout_add(100, check_position)

        self._source.next_ended()
        if self._source.current and self.bin:
            self.bin.set_property('uri', self._source.current("~uri"))

    def stop(self):
        self._end(True, stop=True)

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self._volume = v
            if self.song and config.getboolean("player", "replaygain"):
                profiles = filter(None, self.replaygain_profiles)[0]
                fb_gain = config.getfloat("player", "fallback_gain")
                pa_gain = config.getfloat("player", "pre_amp_gain")
                scale = self.song.replay_gain(profiles, pa_gain, fb_gain)
                v = min(10.0, max(0.0, v * scale)) # volume supports 0..10
            if self.bin:
                self._vol_element.set_property('volume', v)
        else:
            raise AttributeError

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        p = self._last_position
        if self.song and self.bin:
            try: p = self.bin.query_position(gst.FORMAT_TIME)[0]
            except gst.QueryError: pass
            else:
                p //= gst.MSECOND
                # During stream seeking querying the position fails.
                # Better return the last valid one instead of 0.
                self._last_position = p
                # In case the current position is less than at the about to
                # finish signal, we can assume that we are playing a new song.
                # Sometimes the time decreases a bit.. therefore divide by 2
                if self._in_gapless_transition and p < self._finish_position/2:
                    self._end(False)
        return p

    def __buffering(self, percent):
        def stop_buf(*args): self.paused = True

        if percent < 100:
            if self._task:
                self._task.update(percent/100.0)
            else:
                self._task = Task(_("Stream"), _("Buffering"), stop=stop_buf)
        elif self._task:
            self._task.finish()
            self._task = None

        self._set_inhibit_play(percent < 100)

    def _set_inhibit_play(self, inhibit):
        """Set the inhibit play flag.  If set, this will pause the pipeline
        without giving the appearance of being paused to the outside.  This
        is for internal uses of pausing, such as for waiting while the buffer
        is being filled for network streams."""
        if inhibit == self._inhibit_play:
            return

        self._inhibit_play = inhibit
        if inhibit:
            self.bin.set_state(gst.STATE_PAUSED)
        elif not self.paused:
            self.bin.set_state(gst.STATE_PLAYING)

    def _set_paused(self, paused):
        if paused != self._paused:
            self._paused = paused
            if self.song:
                if not self.bin and not paused:
                    if self.__init_pipeline():
                        self.bin.set_property('uri', self.song("~uri"))
                    else:
                        # Backend error; show message and halt playback
                        ErrorMessage(None, _("Output Error"),
                            _("GStreamer output pipeline could not be "
                              "initialized. The pipeline might be invalid, "
                              "or the device may be in use. Check the "
                              "player preferences.")).run()
                        self._paused = paused = True
                self.emit((paused and 'paused') or 'unpaused')
                if self.bin:
                    if not self._paused:
                        if not self._inhibit_play:
                            self.bin.set_state(gst.STATE_PLAYING)
                    elif self.song.is_file:
                        self.bin.set_state(gst.STATE_PAUSED)
                    else:
                        # seekable streams have a duration >= 0
                        try: d = self.bin.query_duration(gst.FORMAT_TIME)[0]
                        except gst.QueryError: d = -1
                        if d >= 0:
                            self.bin.set_state(gst.STATE_PAUSED)
                        else:
                            self.__destroy_pipeline()
            elif paused is True:
                # Something wants us to pause between songs, or when
                # we've got no song playing (probably StopAfterMenu).
                self.emit('paused')
                self.__destroy_pipeline()

    def _get_paused(self): return self._paused
    paused = property(_get_paused, _set_paused)

    def error(self, message, lock):
        print_w(message)
        self.emit('error', self.song, message, lock)
        if not self.paused:
            self.next()

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""
        # Don't allow seeking during gapless. We can't go back to the old song.
        if self.bin and self.song and not self._in_gapless_transition:
            # ensure any pending state changes have completed
            self.bin.get_state()
            pos = max(0, int(pos))
            gst_time = pos * gst.MSECOND
            event = gst.event_new_seek(
                1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH,
                gst.SEEK_TYPE_SET, gst_time, gst.SEEK_TYPE_NONE, 0)
            if self.bin.send_event(event):
                self._last_position = pos
                self.emit('seek', self.song, pos)

    def _end(self, stopped, stop=False):
        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        song, info = self.song, self.info
        self.song = self.info = None
        self.emit('song-ended', song, stopped)
        if song is not info:
            self.emit('song-ended', info, stopped)

        # Then, set up the next song.
        if not stop:
            self.song = self.info = self._source.current
        self.emit('song-started', self.song)

        if self.song is not None:
            self.volume = self.volume
            if not self._in_gapless_transition:
                # Due to extensive problems with playbin2, we destroy the
                # entire pipeline and recreate it each time we're not in
                # a gapless transition.
                self.__destroy_pipeline()
                if self.__init_pipeline():
                    self.bin.set_property('uri', self.song("~uri"))
                else: self.paused = True
            if self.bin:
                if self.paused:
                    self.bin.set_state(gst.STATE_PAUSED)
                else:
                    self.bin.set_state(gst.STATE_PLAYING)
        else:
            self.__destroy_pipeline()
            self.paused = True

        self._in_gapless_transition = False

    def __tag(self, tags, librarian):
        if self.song and self.song.multisong:
            self._fill_stream(tags, librarian)
        elif self.song and self.song.fill_metadata:
            pass

    def _fill_stream(self, tags, librarian):
        # get a new remote file
        new_info = type(self.song)(self.song["~filename"])
        new_info.multisong = False

        # copy from the old songs
        # we should probably listen to the library for self.song changes
        new_info.update(self.song)
        new_info.update(self.info)

        changed = False
        info_changed = False
        for k in tags.keys():
            value = str(tags[k]).strip()
            if not value: continue
            if k == "bitrate":
                try: bitrate = int(value) / 1000
                except (ValueError, TypeError): pass
                else:
                    if bitrate != self.song.get("~#bitrate"):
                        changed = info_changed = True
                        self.song["~#bitrate"] = bitrate
                        new_info["~#bitrate"] = bitrate
            elif k == "duration":
                try: length = int(long(value) / gst.SECOND)
                except (ValueError, TypeError): pass
                else:
                    if length != self.info.get("~#length"):
                        info_changed = True
                        new_info["~#length"] = length
            elif k in ["emphasis", "mode", "layer", "maximum-bitrate",
                "minimum-bitrate", "has-crc"]:
                continue
            else:
                value = util.decode(value)
                k = {"track-number": "tracknumber",
                     "location": "website"}.get(k, k)
                if self.info.get(k) != value:
                    new_info[k] = value
                    info_changed = True
                if k != "title" and self.song.get(k) != value:
                    self.song[k] = value
                    changed = True

        if info_changed:
            # in case the title changed, make self.info a new instance
            # and emit ended/started for the the old/new one
            if self.info.get("title") != new_info.get("title"):
                if self.info is not self.song:
                    self.emit('song-ended', self.info, False)
                self.info = new_info
                self.emit('song-started', self.info)
            else:
                # in case title didn't changed, update the values of the
                # old instance and tell the library.
                self.info.update(new_info)
                librarian.changed([self.info])

        if changed:
            librarian.changed([self.song])

    @property
    def eq_bands(self):
        if self._eq_element:
            return [29, 59, 119, 237, 474, 947, 1889, 3770, 7523, 15011]
        else:
            return []

    def update_eq_values(self):
        if self._eq_element:
            for band, val in enumerate(self._eq_values):
                self._eq_element.set_property('band%d' % band, val)

def can_play_uri(uri):
    return gst.element_make_from_uri(gst.URI_SRC, uri, '') is not None

def init(librarian):
    gst.debug_set_default_threshold(gst.LEVEL_ERROR)
    if gst.element_make_from_uri(
        gst.URI_SRC,
        "file:///fake/path/for/gst", ""):
        return GStreamerPlayer(librarian)
    else:
        raise PlayerError(
            _("Unable to open input files"),
            _("GStreamer has no element to handle reading files. Check "
                "your GStreamer installation settings."))
