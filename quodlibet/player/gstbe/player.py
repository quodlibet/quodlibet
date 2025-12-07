# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Steven Robertson,
#           2011-2014 Christoph Reiter
#           2020-2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import gi

try:
    gi.require_version("Gst", "1.0")
    gi.require_version("GstPbutils", "1.0")
except ValueError as e:
    raise ImportError(e) from e

from gi.repository import Gst, GLib, GstPbutils

from quodlibet import const
from quodlibet import config
from quodlibet import util
from quodlibet import app
from quodlibet import _

from quodlibet.util import (
    fver,
    sanitize_tags,
    MainRunner,
    MainRunnerError,
    MainRunnerAbortedError,
    MainRunnerTimeoutError,
    print_w,
    print_d,
    print_e,
    print_,
)
from quodlibet.util.path import uri2gsturi
from quodlibet.player import PlayerError
from quodlibet.player._base import BasePlayer
from quodlibet.qltk.notif import Task
from quodlibet.formats.mod import ModFile

from .util import (
    parse_gstreamer_taglist,
    TagListWrapper,
    iter_to_list,
    gstreamer_sink,
    link_many,
    bin_debug,
    AudioSinks,
)
from .plugins import GStreamerPluginHandler
from .prefs import GstPlayerPreferences

STATE_CHANGE_TIMEOUT = Gst.SECOND * 4
GST_PLAY_FLAG_VIDEO = 1 << 0
GST_PLAY_FLAG_TEXT = 1 << 2

const.MinVersions.GSTREAMER.check(Gst.version())


class BufferingWrapper:
    """A wrapper for a Gst.Element (usually GstPlayBin) which pauses the
    elmement in case buffering is needed, but hides the fact that it does.

    Probably not perfect...

    You have to call destroy() before it gets gc'd
    """

    def __init__(self, bin_, player):
        """
        bin_ -- the GstPlaybin instance to wrap
        player -- the GStreamerPlayer instance used
                  for aborting the buffer process
        """

        self.bin = bin_
        self._wanted_state = None
        self._task = None
        self._inhibit_play = False
        self._player = player

        bus = self.bin.get_bus()
        bus.add_signal_watch()
        self.__bus_id = bus.connect("message", self.__message)

    def __message(self, bus, message):
        if message.type == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            self.__update_buffering(percent)

    def __getattr__(self, name):
        return getattr(self.bin, name)

    def __update_buffering(self, percent):
        """Call this with buffer percent values from the bus"""

        if self._task:
            self._task.update(percent / 100.0)

        self.__set_inhibit_play(percent < 100)

    def __set_inhibit_play(self, inhibit):
        """Change the inhibit state"""

        if inhibit == self._inhibit_play:
            return
        self._inhibit_play = inhibit

        # task management
        if inhibit:
            if not self._task:

                def stop_buf(*args):
                    self._player.paused = True

                self._task = Task(_("Stream"), _("Buffering"), stop=stop_buf)
        elif self._task:
            self._task.finish()
            self._task = None

        # state management
        if inhibit:
            # save the current state
            status, state, pending = self.bin.get_state(timeout=STATE_CHANGE_TIMEOUT)
            if status == Gst.StateChangeReturn.SUCCESS and state == Gst.State.PLAYING:
                self._wanted_state = state
            else:
                # no idea, at least don't play
                self._wanted_state = Gst.State.PAUSED

            self.bin.set_state(Gst.State.PAUSED)
        else:
            # restore the old state
            self.bin.set_state(self._wanted_state)
            self._wanted_state = None

    def set_state(self, state):
        if self._inhibit_play:
            # PLAYING, PAUSED change the state for after buffering is finished,
            # everything else aborts buffering
            if state not in (Gst.State.PLAYING, Gst.State.PAUSED):
                # abort
                self.__set_inhibit_play(False)
                self.bin.set_state(state)
                return
            self._wanted_state = state
        else:
            self.bin.set_state(state)

    def get_state(self, *args, **kwargs):
        # get_state also is a barrier (seek/positioning),
        # so call every time but ignore the result in the inhibit case
        res = self.bin.get_state(*args, **kwargs)
        if self._inhibit_play:
            return (
                Gst.StateChangeReturn.SUCCESS,
                self._wanted_state,
                Gst.State.VOID_PENDING,
            )
        return res

    def destroy(self):
        if self.__bus_id:
            bus = self.bin.get_bus()
            bus.disconnect(self.__bus_id)
            bus.remove_signal_watch()
            self.__bus_id = None

        self.__set_inhibit_play(False)
        self.bin = None


def sink_has_external_state(sink: Gst.Element) -> bool:
    try:
        sink_type = AudioSinks(sink.get_factory().get_name())
    except TypeError:
        return False
    if sink_type == AudioSinks.WASAPI:
        # https://bugzilla.gnome.org/show_bug.cgi?id=796386
        return hasattr(sink.props, "volume")
    return sink_type == AudioSinks.PULSE


def sink_state_is_valid(sink):
    if not sink_has_external_state(sink):
        return True

    # pulsesink volume is only valid in PAUSED/PLAYING
    # https://bugzilla.gnome.org/show_bug.cgi?id=748577
    current_state = sink.get_state(0)[1]
    return current_state >= Gst.State.PAUSED


class Seeker:
    """Manages async seeking and position reporting for a pipeline.

    You have to call destroy() before it gets gc'd
    """

    def __init__(self, playbin, player):
        self._player = player
        self._playbin = playbin

        self._last_position = 0
        self._seek_requests = []
        self._active_seeks = []
        self._seekable = False

        bus = playbin.get_bus()
        bus.add_signal_watch()
        self._bus_id = bus.connect("message", self._on_message)
        player.notify("seekable")

    @property
    def seekable(self):
        """If the current stream is seekable"""

        return self._seekable

    def destroy(self):
        """This needs to be called before it gets GC'ed"""

        del self._seek_requests[:]
        del self._active_seeks[:]

        if self._bus_id:
            bus = self._playbin.get_bus()
            bus.disconnect(self._bus_id)
            bus.remove_signal_watch()
            self._bus_id = None

        self._player = None
        self._playbin = None

    def set_position(self, pos):
        """Set the position. Async and might not succeed.

        Args:
            pos (int): position in milliseconds
        """

        pos = max(0, int(pos))

        # We need at least a paused state to seek, if there is non active
        # or pending, request one async.
        res, next_state, pending = self._playbin.get_state(timeout=0)
        if pending != Gst.State.VOID_PENDING:
            next_state = pending
        if next_state < Gst.State.PAUSED:
            self._playbin.set_state(Gst.State.PAUSED)

        self._set_position(self._player.song, pos)

    def get_position(self):
        """Get the position

        Returns:
            int: the position in milliseconds
        """

        if self._seek_requests:
            self._last_position = self._seek_requests[-1][1]
        elif self._active_seeks:
            self._last_position = self._active_seeks[-1][1]
        else:
            # While we are actively seeking return the last wanted position.
            # query_position() returns 0 while in this state
            ok, p = self._playbin.query_position(Gst.Format.TIME)
            if ok:
                p //= Gst.MSECOND
                # During stream seeking querying the position fails.
                # Better return the last valid one instead of 0.
                self._last_position = p

        return self._last_position

    def reset(self):
        """In case the underlying stream has changed, call this to
        abort any pending seeking actions and update the seekable state
        """

        self._last_position = 0
        del self._seek_requests[:]
        del self._active_seeks[:]
        self._refresh_seekable()

    def _refresh_seekable(self):
        query = Gst.Query.new_seeking(Gst.Format.TIME)
        if self._playbin.query(query):
            seekable = query.parse_seeking()[1]
        elif self._player.song is None:
            seekable = False
        else:
            seekable = True

        if seekable != self._seekable:
            self._seekable = seekable
            self._player.notify("seekable")

    def _on_message(self, bus, message):
        if message.type == Gst.MessageType.ASYNC_DONE:
            # we only get one ASYNC_DONE for multiple seeks, so flush all

            if self._active_seeks:
                song, pos = self._active_seeks[-1]
                if song is self._player.song:
                    self._player.emit("seek", song, pos)
                del self._active_seeks[:]
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src is self._playbin.bin:
                new_state = message.parse_state_changed()[1]
                if new_state >= Gst.State.PAUSED:
                    self._refresh_seekable()

                    if self._seek_requests:
                        song, pos = self._seek_requests[-1]
                        if song is self._player.song:
                            self._set_position(song, pos)
                        del self._seek_requests[:]

    def _set_position(self, song, pos):
        event = Gst.Event.new_seek(
            1.0,
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH,
            Gst.SeekType.SET,
            pos * Gst.MSECOND,
            Gst.SeekType.NONE,
            0,
        )

        if self._playbin.send_event(event):
            self._active_seeks.append((song, pos))
        else:
            self._seek_requests.append((song, pos))


class GStreamerPlayer(BasePlayer, GStreamerPluginHandler):
    def PlayerPreferences(self):  # noqa
        return GstPlayerPreferences(self, const.DEBUG)

    def __init__(self, librarian=None):
        GStreamerPluginHandler.__init__(self)
        BasePlayer.__init__(self)

        self._librarian = librarian

        self.version_info = f"GStreamer: {fver(Gst.version())}"
        self._pipeline_desc = None

        self._volume = 1.0
        self._paused = True
        self._mute = False

        self._in_gapless_transition = False
        self._active_error = False

        self.bin = None
        self._seeker = None
        self._int_vol_element = None
        self._ext_vol_element = None
        self._ext_mute_element = None
        self._use_eq = False
        self._eq_element = None
        self.__info_buffer = None

        self._lib_id = librarian.connect("changed", self.__songs_changed)
        self.__atf_id = None
        self.__bus_id = None
        self._runner = MainRunner()

    def __songs_changed(self, librarian, songs):
        # replaygain values might have changed, recalc volume
        if self.song and self.song in songs:
            self._reset_replaygain()

    def _destroy(self):
        self._librarian.disconnect(self._lib_id)
        self._runner.abort()
        self.__destroy_pipeline()

    @property
    def name(self):
        name = "GStreamer"
        if self._pipeline_desc:
            name += f" ({self._pipeline_desc})"
        return name

    @property
    def has_external_volume(self):
        ext = self._ext_vol_element
        if ext is None or not sink_has_external_state(ext):
            return False
        return True

    def _set_buffer_duration(self, duration):
        """Set the stream buffer duration in msecs"""

        config.set("player", "gst_buffer", float(duration) / 1000)

        if self.bin:
            value = duration * Gst.MSECOND
            self.bin.set_property("buffer-duration", value)

    def _print_pipeline(self):
        """Print debug information for the active pipeline to stdout
        (elements, formats, ...)
        """

        if self.bin:
            # self.bin is just a wrapper, so get the real one
            for line in bin_debug([self.bin.bin]):
                print_(line)
        else:
            print_e("No active pipeline.")

    def _make(self, el, name=None):
        return Gst.ElementFactory.make(el, name)

    def __init_pipeline(self):
        """Creates a gstreamer pipeline. Returns True on success."""

        if self.bin:
            return True

        # reset error state
        self.error = False

        pipeline = config.get("player", "gst_pipeline")
        print_d(f"User pipeline (from player.gst_pipeline): {pipeline!r}")
        try:
            pipeline, self._pipeline_desc = gstreamer_sink(pipeline)
        except PlayerError as e:
            self._error(e)
            return False

        if self._use_eq and Gst.ElementFactory.find("equalizer-10bands"):
            # The equalizer only operates on 16-bit ints or floats, and
            # will only pass these types through even when inactive.
            # We push floats through to this point, then let the second
            # audioconvert handle pushing to whatever the rest of the
            # pipeline supports. As a bonus, this seems to automatically
            # select the highest-precision format supported by the
            # rest of the chain.
            print_d("Setting up Gstreamer equalizer")
            filt = self._make("capsfilter", None)
            filt.set_property("caps", Gst.Caps.from_string("audio/x-raw,format=F32LE"))
            eq = self._make("equalizer-10bands", None)
            self._eq_element = eq
            self.update_eq_values()
            conv = self._make("audioconvert", None)
            resample = self._make("audioresample", None)
            pipeline = [filt, eq, conv, resample] + pipeline

        # playbin2 has started to control the volume through pulseaudio,
        # which means the volume property can change without us noticing.
        # Use our own volume element for now until this works with PA.
        self._int_vol_element = self._make("volume", None)
        pipeline.insert(0, self._int_vol_element)

        # Get all plugin elements and append audio converters.
        # playbin already includes one at the end
        plugin_pipeline = []
        for plugin in self._get_plugin_elements():
            plugin_pipeline.append(plugin)
            plugin_pipeline.append(self._make("audioconvert", None))
            plugin_pipeline.append(self._make("audioresample", None))
        print_d(f"GStreamer plugin pipeline: {plugin_pipeline}")
        pipeline = plugin_pipeline + pipeline

        bufbin = Gst.Bin()
        for element in pipeline:
            assert element is not None, pipeline
            bufbin.add(element)

        if len(pipeline) > 1:
            try:
                link_many(pipeline)
            except OSError as e:
                print_w("Linking the GStreamer pipeline failed")
                self._error(
                    PlayerError(_("Could not create GStreamer pipeline (%s)") % e)
                )
                return False

        # see if the sink provides a volume property, if yes, use it
        sink_element = pipeline[-1]
        if isinstance(sink_element, Gst.Bin):
            sink_element = iter_to_list(sink_element.iterate_recurse)[-1]

        self._ext_vol_element = None
        if hasattr(sink_element.props, "volume"):
            self._ext_vol_element = sink_element

            # In case we use the sink volume directly we can increase buffering
            # without affecting the volume change delay too much and save some
            # CPU time... (2x default for now).
            if hasattr(sink_element.props, "buffer_time"):
                sink_element.set_property("buffer-time", 400000)

            def ext_volume_notify(*args):
                # gets called from a thread
                GLib.idle_add(self.notify, "volume")

            self._ext_vol_element.connect("notify::volume", ext_volume_notify)

        self._ext_mute_element = None
        if (
            hasattr(sink_element.props, "mute")
            and sink_element.get_factory().get_name() != "directsoundsink"
        ):
            # directsoundsink has a mute property but it doesn't work
            # https://bugzilla.gnome.org/show_bug.cgi?id=755106
            self._ext_mute_element = sink_element

            def mute_notify(*args):
                # gets called from a thread
                GLib.idle_add(self.notify, "mute")

            self._ext_mute_element.connect("notify::mute", mute_notify)

        # Make the sink of the first element the sink of the bin
        gpad = Gst.GhostPad.new("sink", pipeline[0].get_static_pad("sink"))
        bufbin.add_pad(gpad)

        if config.getboolean("player", "gst_use_playbin3"):
            bin_ = self._make("playbin3", None)
        else:
            bin_ = self._make("playbin", None)
        assert bin_

        self.bin = BufferingWrapper(bin_, self)
        self._seeker = Seeker(self.bin, self)

        bus = bin_.get_bus()
        bus.add_signal_watch()
        self.__bus_id = bus.connect("message", self.__message, self._librarian)

        self.__atf_id = self.bin.connect("about-to-finish", self.__about_to_finish)

        # set buffer duration
        duration = config.getfloat("player", "gst_buffer")
        self._set_buffer_duration(int(duration * 1000))

        # connect playbin to our plugin / volume / EQ pipeline
        self.bin.set_property("audio-sink", bufbin)

        # by default playbin will render video -> suppress using fakesink
        vsink = self._make(AudioSinks.FAKE.value, None)
        self.bin.set_property("video-sink", vsink)

        # disable all video/text decoding in playbin
        flags = self.bin.get_property("flags")
        flags &= ~(GST_PLAY_FLAG_VIDEO | GST_PLAY_FLAG_TEXT)
        self.bin.set_property("flags", flags)

        if not self.has_external_volume:
            # Restore volume/ReplayGain and mute state
            self.props.volume = self._volume
            self.mute = self._mute

        # ReplayGain information gets lost when destroying
        self._reset_replaygain()

        if self.song:
            self._set_uri(self.song("~uri"))

        return True

    def _set_uri(self, uri: str) -> None:
        self.bin.set_property("uri", uri2gsturi(uri))

    def __destroy_pipeline(self):
        print_d("Destroying Gstreamer pipeline")
        self._remove_plugin_elements()

        if self.__bus_id:
            bus = self.bin.get_bus()
            bus.disconnect(self.__bus_id)
            bus.remove_signal_watch()
            self.__bus_id = None

        if self.__atf_id:
            self.bin.disconnect(self.__atf_id)
            self.__atf_id = None

        if self._seeker is not None:
            self._seeker.destroy()
            self._seeker = None
            self.notify("seekable")

        if self.bin:
            self.bin.set_state(Gst.State.NULL)
            self.bin.get_state(timeout=STATE_CHANGE_TIMEOUT)
            # BufferingWrapper cleanup
            self.bin.destroy()
            self.bin = None

        self._in_gapless_transition = False

        self._ext_vol_element = None
        self._int_vol_element = None
        self._ext_mute_element = None
        self._eq_element = None

    def _rebuild_pipeline(self):
        """If a pipeline is active, rebuild it and restore vol, position etc"""

        if not self.bin:
            return

        paused = self.paused
        pos = self.get_position()

        self.__destroy_pipeline()
        self.paused = True
        self.__init_pipeline()
        self.paused = paused
        self.seek(pos)

    def __message(self, bus, message, librarian):
        if message.type == Gst.MessageType.EOS:
            print_d("Stream EOS")
            if not self._in_gapless_transition:
                self._source.next_ended()
            self._end(False)
        elif message.type == Gst.MessageType.TAG:
            self.__tag(message.parse_tag(), librarian)
        elif message.type == Gst.MessageType.ERROR:
            gerror, debug_info = message.parse_error()
            message = ""
            if gerror:
                message = gerror.message.rstrip(".")
            details = None
            if debug_info:
                # strip the first line, not user friendly
                debug_info = "\n".join(debug_info.splitlines()[1:])
                # can contain paths, so not sure if utf-8 in all cases
                details = debug_info
            self._error(PlayerError(message, details))
        elif message.type == Gst.MessageType.STATE_CHANGED:
            # pulsesink doesn't notify a volume change on startup
            # and the volume is only valid in > paused states.
            if message.src is self._ext_vol_element:
                self.notify("volume")
            if message.src is self._ext_mute_element:
                self.notify("mute")
        elif message.type == Gst.MessageType.STREAM_START:
            if self._in_gapless_transition:
                print_d("Stream changed")
                self._end(False)
        elif message.type == Gst.MessageType.ELEMENT:
            message_name = message.get_structure().get_name()

            if message_name == "missing-plugin":
                self.__handle_missing_plugin(message)
        elif message.type == Gst.MessageType.CLOCK_LOST:
            print_d("Clock lost")
            self.bin.set_state(Gst.State.PAUSED)
            self.bin.set_state(Gst.State.PLAYING)
        elif message.type == Gst.MessageType.LATENCY:
            print_d("Recalculate latency")
            self.bin.recalculate_latency()
        elif message.type == Gst.MessageType.REQUEST_STATE:
            state = message.parse_request_state()
            print_d(f"State requested: {Gst.Element.state_get_name(state)}")
            self.bin.set_state(state)
        elif message.type == Gst.MessageType.DURATION_CHANGED:
            if self.song.fill_length:
                ok, p = self.bin.query_duration(Gst.Format.TIME)
                if ok:
                    p /= float(Gst.SECOND)
                    self.song["~#length"] = p
                    librarian.changed([self.song])

    def __handle_missing_plugin(self, message):
        get_installer_detail = GstPbutils.missing_plugin_message_get_installer_detail
        get_description = GstPbutils.missing_plugin_message_get_description

        details = get_installer_detail(message)
        if details is None:
            return

        self.stop()

        format_desc = get_description(message)
        title = _("No GStreamer element found to handle media format")
        error_details = _("Media format: %(format-description)s") % {
            "format-description": format_desc
        }

        def install_done_cb(plugins_return, *args):
            print_d(f"Gstreamer plugin install return: {plugins_return!r}")
            Gst.update_registry()

        context = GstPbutils.InstallPluginsContext.new()

        # new in 1.6
        if hasattr(context, "set_desktop_id"):
            from gi.repository import Gtk

            context.set_desktop_id(app.id)

        # new in 1.6
        if hasattr(context, "set_startup_notification_id"):
            current_time = Gtk.get_current_event_time()
            context.set_startup_notification_id("_TIME%d" % current_time)

        gdk_window = app.window.get_window()
        if gdk_window:
            try:
                xid = gdk_window.get_xid()
            except AttributeError:  # non X11
                pass
            else:
                context.set_xid(xid)

        res = GstPbutils.install_plugins_async(
            [details], context, install_done_cb, None
        )
        print_d(f"Gstreamer plugin install result: {res!r}")

        if res in (
            GstPbutils.InstallPluginsReturn.HELPER_MISSING,
            GstPbutils.InstallPluginsReturn.INTERNAL_FAILURE,
        ):
            self._error(PlayerError(title, error_details))

    def __about_to_finish_sync(self):
        """Returns the next song uri to play or None"""

        print_d("About to finish (sync)")

        # Chained oggs falsely trigger a gapless transition.
        # At least for radio streams we can safely ignore it because
        # transitions don't occur there.
        # https://github.com/quodlibet/quodlibet/issues/1454
        # https://bugzilla.gnome.org/show_bug.cgi?id=695474
        if self.song and self.song.multisong:
            print_d("This is a multisong - so ignoring 'about to finish' signal")
            return None

        # mod + gapless deadlocks
        # https://github.com/quodlibet/quodlibet/issues/2780
        if isinstance(self.song, ModFile):
            return None

        if config.getboolean("player", "gst_disable_gapless"):
            print_d("Gapless disabled")
            return None

        # this can trigger twice, see issue 987
        if self._in_gapless_transition:
            return None
        self._in_gapless_transition = True

        print_d("Select next song in mainloop…")
        self._source.next_ended()
        print_d("…next song done.")

        song = self._source.current
        if song is not None:
            return song("~uri")
        return None

    def __about_to_finish(self, playbin):
        print_d("About to finish (async)")

        try:
            uri = self._runner.call(
                self.__about_to_finish_sync, priority=GLib.PRIORITY_HIGH, timeout=0.5
            )
        except MainRunnerTimeoutError as e:
            # Due to some locks being held during this signal we can get
            # into a deadlock when a seek or state change event happens
            # in the mainloop before our function gets scheduled.
            # In this case abort and do nothing, which results
            # in a non-gapless transition.
            print_e(f"About to finish (async): {e!r}")
            return
        except MainRunnerAbortedError as e:
            print_e(f"About to finish (async): {e!r}")
            return
        except MainRunnerError:
            util.print_exc()
            return

        if uri is not None:
            print_d(f"About to finish (async): setting URI to {uri}")
            self._set_uri(uri)
        print_d("About to finish (async): done")

    def stop(self):
        super().stop()
        print_d("Stop playing")
        self.__destroy_pipeline()

    def do_get_property(self, property):
        if property.name == "volume":
            if (
                self._ext_vol_element is not None
                and sink_has_external_state(self._ext_vol_element)
                and sink_state_is_valid(self._ext_vol_element)
            ):
                # never read back the volume if we don't have to, e.g.
                # directsoundsink maps volume to an int which makes UI
                # sliders jump if we read the value back
                self._volume = self._ext_vol_element.get_property("volume")
            return self._volume
        if property.name == "mute":
            if (
                self._ext_mute_element is not None
                and sink_has_external_state(self._ext_mute_element)
                and sink_state_is_valid(self._ext_mute_element)
            ):
                self._mute = self._ext_mute_element.get_property("mute")
            return self._mute
        if property.name == "seekable":
            if self._seeker is not None:
                return self._seeker.seekable
            return False
        raise AttributeError

    def _reset_replaygain(self):
        if not self.bin:
            return

        v = 1.0 if self._ext_vol_element is not None else self._volume
        v = self.calc_replaygain_volume(v)
        v = min(10.0, max(0.0, v))
        self._int_vol_element.set_property("volume", v)

    def do_set_property(self, property, v):
        if property.name == "volume":
            self._volume = v
            if self._ext_vol_element:
                v = min(10.0, max(0.0, v))
                self._ext_vol_element.set_property("volume", v)
            else:
                v = self.calc_replaygain_volume(v)
                if self.bin:
                    v = min(10.0, max(0.0, v))
                    self._int_vol_element.set_property("volume", v)
        elif property.name == "mute":
            self._mute = v
            if self._ext_mute_element is not None:
                self._ext_mute_element.set_property("mute", v)
            else:
                if self.bin:
                    self._int_vol_element.set_property("mute", v)
        else:
            raise AttributeError

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""

        if self._seeker:
            return self._seeker.get_position()
        return 0

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, paused):
        if paused == self._paused:
            return

        self._paused = paused
        self.emit((paused and "paused") or "unpaused")
        # in case a signal handler changed the paused state, abort this
        if self._paused != paused:
            return

        if paused:
            if self.bin:
                if not self.song:
                    # Something wants us to pause between songs, or when
                    # we've got no song playing (probably StopAfterMenu).
                    self.__destroy_pipeline()
                elif self.seekable:
                    self.bin.set_state(Gst.State.PAUSED)
                else:
                    q = Gst.Query.new_buffering(Gst.Format.DEFAULT)
                    if self.bin.query(q):
                        # destroy so that we rebuffer on resume i.e. we don't
                        # want to continue unseekable streams from where we
                        # paused but from where we unpaused.
                        self.__destroy_pipeline()
                    else:
                        self.bin.set_state(Gst.State.PAUSED)
        else:
            if self.song and self.__init_pipeline():
                self.bin.set_state(Gst.State.PLAYING)

    def _error(self, player_error):
        """Destroy the pipeline and set the error state.

        The passed PlayerError will be emitted through the 'error' signal.
        """

        # prevent recursive errors
        if self._active_error:
            return
        self._active_error = True

        self.__destroy_pipeline()
        self.error = True
        self.paused = True

        print_w(player_error)
        self.emit("error", self.song, player_error)
        self._active_error = False

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""

        # Don't allow seeking during gapless. We can't go back to the old song.
        if not self.song or self._in_gapless_transition:
            return

        if self.__init_pipeline():
            self._seeker.set_position(pos)

    def sync(self, timeout):
        if self.bin is not None:
            # XXX: This is flaky, try multiple times
            for _i in range(5):
                self.bin.get_state(Gst.SECOND * timeout)
                # we have some logic in the main loop, so iterate there
                while GLib.MainContext.default().iteration(False):
                    pass

    def _end(self, stopped, next_song=None):
        print_d("End song")
        song, info = self.song, self.info

        # set the new volume before the signals to avoid delays
        if self._in_gapless_transition:
            self.song = self._source.current
            self._reset_replaygain()

        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        self.__info_buffer = self.song = self.info = None
        if song is not info:
            self.emit("song-ended", info, stopped)
        self.emit("song-ended", song, stopped)

        current = next_song if next_song else (self._source and self._source.current)

        # Then, set up the next song.
        self.song = self.info = current

        if self.song is not None:
            if not self._in_gapless_transition:
                # Due to extensive problems with playbin2, we destroy the
                # entire pipeline and recreate it each time we're not in
                # a gapless transition.
                self.__destroy_pipeline()
                self.__init_pipeline()
            if self.bin:
                if self.paused:
                    self.bin.set_state(Gst.State.PAUSED)
                else:
                    # something unpaused while no song was active
                    if song is None:
                        self.emit("unpaused")
                    self.bin.set_state(Gst.State.PLAYING)
        else:
            self.__destroy_pipeline()

        self._in_gapless_transition = False

        if self._seeker is not None:
            # we could have a gapless transition to a non-seekable -> update
            self._seeker.reset()

        self.emit("song-started", self.song)

        if self.song is None:
            self.paused = True

    def __tag(self, tags, librarian):
        if self.song and self.song.multisong:
            self._fill_stream(tags, librarian)
        elif self.song and self.song.fill_metadata:
            pass

    def _fill_stream(self, tags, librarian):
        # get a new remote file
        new_info = self.__info_buffer
        if not new_info:
            new_info = type(self.song)(self.song["~filename"])
            new_info.multisong = False
            new_info.streamsong = True

            # copy from the old songs
            # we should probably listen to the library for self.song changes
            new_info.update(self.song)
            new_info.update(self.info)

        changed = False
        info_changed = False

        tags = TagListWrapper(tags, merge=True)
        tags = parse_gstreamer_taglist(tags)

        for key, value in sanitize_tags(tags, stream=False).items():
            if self.song.get(key) != value:
                changed = True
                self.song[key] = value

        for key, value in sanitize_tags(tags, stream=True).items():
            if new_info.get(key) != value:
                info_changed = True
                new_info[key] = value

        if info_changed:
            # in case the title changed, make self.info a new instance
            # and emit ended/started for the old/new one
            if self.info.get("title") != new_info.get("title"):
                if self.info is not self.song:
                    self.emit("song-ended", self.info, False)
                self.info = new_info
                self.__info_buffer = None
                self.emit("song-started", self.info)
            else:
                # in case title didn't change, update the values of the
                # old instance if there is one and tell the library.
                if self.info is not self.song:
                    self.info.update(new_info)
                    librarian.changed([self.info])
                else:
                    # So we don't lose all tags before the first title
                    # save it for later
                    self.__info_buffer = new_info

        if changed:
            librarian.changed([self.song])

    @property
    def eq_bands(self):
        if Gst.ElementFactory.find("equalizer-10bands"):
            return [29, 59, 119, 237, 474, 947, 1889, 3770, 7523, 15011]
        return []

    def update_eq_values(self):
        need_eq = any(self._eq_values)
        if need_eq != self._use_eq:
            self._use_eq = need_eq
            self._rebuild_pipeline()

        if self._eq_element:
            for band, val in enumerate(self._eq_values):
                self._eq_element.set_property("band%d" % band, val)

    def can_play_uri(self, uri):
        if not Gst.uri_is_valid(uri):
            return False
        try:
            Gst.Element.make_from_uri(Gst.URIType.SRC, uri, "")
        except GLib.GError:
            return False
        return True


def init(librarian):
    # Enable error messages by default
    if Gst.debug_get_default_threshold() == Gst.DebugLevel.NONE:
        Gst.debug_set_default_threshold(Gst.DebugLevel.ERROR)

    return GStreamerPlayer(librarian)
