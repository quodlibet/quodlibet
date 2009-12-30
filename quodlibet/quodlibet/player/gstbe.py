# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gobject

import pygst
pygst.require("0.10")

import gst
if gst.pygst_version >= (0, 10, 10):
    import gst.pbutils

from quodlibet import config
from quodlibet import const

from quodlibet.util import fver
from quodlibet.player import error as PlayerError
from quodlibet.player._base import BasePlayer
from quodlibet.qltk.msg import ErrorMessage

def GStreamerSink(pipeline):
    """Try to create a GStreamer pipeline:
    * Try making the pipeline (defaulting to gconfaudiosink).
    * If it fails, fall back to autoaudiosink.
    * If that fails, complain loudly.

    Returns the pipeline's description and a list of disconnected elements."""

    if pipeline == "gconf": pipeline = "gconfaudiosink profile=music"
    try: pipe = [gst.parse_launch(element) for element in pipeline.split('!')]
    except gobject.GError, err:
        print_w(_("Invalid GStreamer output pipeline, trying default."))
        if pipeline != "autoaudiosink":
            try: pipe = [gst.parse_launch("autoaudiosink")]
            except gobject.GError: pipe = None
            else: pipeline = "autoaudiosink"
        else: pipe = None
    if pipe: return pipe, pipeline
    else:
        raise PlayerError(
            _("Unable to create audio output"),
            _("The audio output pipeline %r could not be created. Check "
              "your GStreamer settings in ~/.quodlibet/config.") % pipeline)

class GStreamerPlayer(BasePlayer):
    __gproperties__ = BasePlayer._gproperties_
    __gsignals__ = BasePlayer._gsignals_

    def __init__(self, librarian=None):
        super(GStreamerPlayer, self).__init__()
        self.version_info = "GStreamer: %s / PyGSt: %s" % (
            fver(gst.version()), fver(gst.pygst_version))
        self.librarian = librarian
        self.name = ''
        self.bin = None
        self.connect('destroy', lambda s: self.__destroy_pipeline())
        self._in_gapless_transition = False
        self.paused = True

    def __init_pipeline(self):
        if self.bin: return True
        pipeline = (config.get("player", "gst_pipeline") or
                    "gconfaudiosink profile=music")
        pipeline, self.name = GStreamerSink(pipeline)
        if gst.version() >= (0, 10, 24):
            # The output buffer is necessary to run the song-ended and
            # song-started events through QL's signal handlers before the
            # playbin2 hits EOF inside a gapless transition.
            bufbin = gst.Bin()
            queue = gst.element_factory_make('queue')
            queue.set_property('max-size-time', 500 * gst.MSECOND)
            self._vol_element = vol = gst.element_factory_make('volume')
            pipeline = [queue, vol] + pipeline
            for idx, elem in enumerate(pipeline):
                bufbin.add(elem)
                if idx > 0:
                    pipeline[idx-1].link(elem)
            # Test to ensure output pipeline can preroll
            bufbin.set_state(gst.STATE_READY)
            result, state, oldstate = bufbin.get_state()
            bufbin.set_state(gst.STATE_NULL)
            if result == gst.STATE_CHANGE_FAILURE: return False
            gpad = gst.GhostPad('sink', queue.get_pad('sink'))
            bufbin.add_pad(gpad)
            self.bin = gst.element_factory_make('playbin2')
            id = self.bin.connect('about-to-finish', self.__about_to_finish)
            self.__atf_id = id
            self.bin.set_property('audio-sink', bufbin)
        else:
            self.bin = gst.element_factory_make('playbin')
            self.bin.set_property('audio-sink', pipeline[-1])
            self._vol_element = self.bin
            self.__atf_id = None
        self.bin.set_property('video-sink', None)
        # ReplayGain information gets lost when destroying
        self.volume = self.volume
        bus = self.bin.get_bus()
        bus.add_signal_watch()
        self.__bus_id = bus.connect('message', self.__message, self.librarian)
        if gst.pygst_version >= (0, 10, 10):
            self.__elem_id = bus.connect('message::element',
                                         self.__message_elem)
        return True

    def __destroy_pipeline(self):
        if self.bin is None: return
        self.bin.set_state(gst.STATE_NULL)
        bus = self.bin.get_bus()
        bus.disconnect(self.__bus_id)
        if gst.pygst_version >= (0, 10, 10):
            bus.disconnect(self.__elem_id)
        bus.remove_signal_watch()
        if self.__atf_id is not None:
            self.bin.disconnect(self.__atf_id)
        del self.bin
        del self._vol_element
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
        return True

    def __message_elem(self, bus, message):
        if not message.structure.get_name().startswith('missing-'):
            return True
        d = gst.pbutils.missing_plugin_message_get_installer_detail(message)
        ctx = gst.pbutils.InstallPluginsContext()
        gobject.idle_add(self.stop)
        gst.pbutils.install_plugins_async([d], ctx, self.__message_elem_cb)
        return True

    def __message_elem_cb(self, result):
        gst.update_registry()

    def __about_to_finish(self, pipeline):
        self._in_gapless_transition = True
        self._source.next_ended()
        if self._source.current:
            self.bin.set_property('uri', self._source.current("~uri"))
            gobject.timeout_add(0, self._end, False, True,
                             priority = gobject.PRIORITY_HIGH)

    def stop(self):
        # On GStreamer, we can release the device when stopped.
        if not self.paused:
            self._paused = True
            if self.song:
                self.emit('paused')
        self.__destroy_pipeline()

    def do_set_property(self, property, v):
        if property.name == 'volume':
            if self._in_gapless_transition:
                return
            self._volume = v
            if self.song and config.getboolean("player", "replaygain"):
                profiles = filter(None, self.replaygain_profiles)[0]
                fb_gain = config.getfloat("player", "fallback_gain")
                pa_gain = config.getfloat("player", "pre_amp_gain")
                scale = self.song.replay_gain(profiles, pa_gain, fb_gain)
                v = max(0.0, v * scale)
            if self.bin:
                self._vol_element.set_property('volume', v)
        else:
            raise AttributeError

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        if self.song and self.bin:
            try: p = self.bin.query_position(gst.FORMAT_TIME)[0]
            except gst.QueryError: p = 0
            p //= gst.MSECOND
            return p
        else:
            return 0

    def _set_paused(self, paused):
        if paused != self._paused:
            self._paused = paused
            if self.song:
                if not self.bin:
                    if self.__init_pipeline():
                        self.bin.set_property('uri', self.song("~uri"))
                    else:
                        # Backend error; show message and halt playback
                        ErrorMessage(None, _("Output Error"), _("Output "
                            "pipeline could not be initialized.")).run()
                    self._paused = paused = True
                self.emit((paused and 'paused') or 'unpaused')
                if self.bin:
                    if self._paused:
                        self.bin.set_state(gst.STATE_PAUSED)
                    else:
                        self.bin.set_state(gst.STATE_PLAYING)
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
        if self.song is not None:
            # ensure any pending state changes have completed
            self.bin.get_state()
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

    def _end(self, stopped, gapless = False):
        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        song = self.song
        self.song = self.info = None
        self.emit('song-ended', song, stopped)

        # Then, set up the next song.
        self._in_gapless_transition = False
        self.song = self.info = self._source.current
        self.emit('song-started', self.song)

        if self.song is not None:
            self._length = self.info["~#length"] * 1000
            if not gapless:
                # Due to extensive problems with playbin2, we destroy the
                # entire pipeline and recreate it each time we're not in
                # a gapless transition.
                self.__destroy_pipeline()
                if self.__init_pipeline():
                    self.bin.set_property('uri', self.song("~uri"))
                else: self.paused = True
            if self.bin:
                if self._paused:
                    self.bin.set_state(gst.STATE_PAUSED)
                else:
                    self.bin.set_state(gst.STATE_PLAYING)
        else:
            self.__destroy_pipeline()
            self.paused = True

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
