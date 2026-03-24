# Copyright 2009-2011 Steven Robertson, Christoph Reiter
#                2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

try:
    from collections import abc
except ImportError:
    import collections as abc  # type: ignore
import subprocess
from enum import Enum
from collections.abc import Iterable
from gi.repository import GLib, Gst

from quodlibet import _, print_d, config
from quodlibet.util.string import decode
from quodlibet.util import is_linux, is_windows
from quodlibet.player import PlayerError


class AudioSinks(Enum):
    """Relevant Gstreamer sink elements"""

    FAKE = "fakesink"

    DIRECTSOUND = "directsoundsink"

    PULSE = "pulsesink"
    """from plugins-good"""

    ALSA = "alsasink"
    """from plugins-base"""

    AUTO = "autoaudiosink"
    """from plugins-good"""

    JACK = "jackaudiosink"
    """from plugins-good"""

    WASAPI = "wasapisink"

    WASAPI2 = "wasapi2sink"


def pulse_is_running():
    """Returns whether pulseaudio is running"""

    # If we have a pulsesink we can get the server presence through
    # setting the ready state
    element = Gst.ElementFactory.make(AudioSinks.PULSE.value, None)
    if element is not None:
        element.set_state(Gst.State.READY)
        res = element.get_state(0)[0]
        element.set_state(Gst.State.NULL)
        return res != Gst.StateChangeReturn.FAILURE

    # In case we don't have it call the pulseaudio binary
    try:
        subprocess.check_call(["pulseaudio", "--check"])
    except subprocess.CalledProcessError:
        return False
    except OSError:
        return False
    return True


def jack_is_running() -> bool:
    """:returns: whether Jack is running"""

    element = Gst.ElementFactory.make(AudioSinks.JACK.value, "test sink")
    if element:
        element.set_state(Gst.State.READY)
        res = element.get_state(0)[0]
        element.set_state(Gst.State.NULL)
        return res != Gst.StateChangeReturn.FAILURE
    return False


def link_many(elements: Iterable[Gst.Element]) -> None:
    """Links all elements together
    :raises OSError: if they can't all be linked"""
    last = None
    print_d(
        f"Attempting to link Gstreamer element(s): "
        f"{[type(e).__name__ for e in elements]}"
    )
    for element in elements:
        if last:
            if not Gst.Element.link(last, element):
                raise OSError(f"Failed on element: {type(element).__name__}")
        last = element


def unlink_many(elements):
    last = None
    for element in elements:
        if last:
            if not Gst.Element.unlink(last, element):
                return False
        last = element
    return True


def iter_to_list(func):
    objects = []

    iter_ = func()
    while 1:
        status, value = iter_.next()
        if status == Gst.IteratorResult.OK:
            objects.append(value)
        else:
            break
    return objects


def find_audio_sink() -> tuple[Gst.Element, str]:
    """Get the best audio sink available.

    Returns (element, description) or raises PlayerError.
    """

    def sink_options():
        # People with Jack running probably want it more than any other options
        if config.getboolean("player", "gst_use_jack") and jack_is_running():
            print_d("Using JACK output via Gstreamer")
            return [AudioSinks.JACK]
        if is_windows():
            return [AudioSinks.WASAPI2, AudioSinks.DIRECTSOUND]
        if is_linux() and pulse_is_running():
            return [AudioSinks.PULSE]
        return [
            AudioSinks.AUTO,
            AudioSinks.PULSE,
            AudioSinks.ALSA,
        ]

    options = sink_options()
    for sink in options:
        element = Gst.ElementFactory.make(sink.value, "player")
        if sink == AudioSinks.JACK and not config.getboolean(
            "player", "gst_jack_auto_connect"
        ):
            # Disable the auto-connection to outputs (e.g. maybe there's scripting)
            element.set_property("connect", "none")
        if element is not None:
            return element, sink.value
    else:
        details = ", ".join(s.value for s in options) if options else "[]"
        raise PlayerError(_("No GStreamer audio sink found. Tried: %s") % details)


def gstreamer_sink(pipeline_desc):
    """Returns a list of unlinked gstreamer elements ending with an audio sink
    and a textual description of the pipeline.

    `pipeline_desc` can be gst-launch syntax for multiple elements
    with or without an audiosink.

    In case of an error, raises PlayerError
    """

    pipe = None
    if pipeline_desc:
        try:
            pipe = [Gst.parse_launch(e) for e in pipeline_desc.split("!")]
        except GLib.GError as e:
            message = e.message
            raise PlayerError(_("Invalid GStreamer output pipeline"), message) from e

    if pipe:
        # In case the last element is linkable with a fakesink
        # it is not an audiosink, so we append the default one
        fake = Gst.ElementFactory.make(AudioSinks.FAKE.value, None)
        try:
            link_many([pipe[-1], fake])
        except OSError:
            pass
        else:
            unlink_many([pipe[-1], fake])
            default_elm, default_desc = find_audio_sink()
            pipe += [default_elm]
            pipeline_desc += " ! " + default_desc
    else:
        elm, pipeline_desc = find_audio_sink()
        pipe = [elm]

    return pipe, pipeline_desc


class TagListWrapper(abc.Mapping):
    def __init__(self, taglist, merge=False):
        self._list = taglist
        self._merge = merge

    def __len__(self):
        return self._list.n_tags()

    def __iter__(self):
        for i in range(len(self)):
            yield self._list.nth_tag_name(i)

    def __getitem__(self, key):
        if not Gst.tag_exists(key):
            raise KeyError

        values = []
        index = 0
        while 1:
            value = self._list.get_value_index(key, index)
            if value is None:
                break
            values.append(value)
            index += 1

        if not values:
            raise KeyError

        if self._merge:
            try:
                return " - ".join(values)
            except TypeError:
                return values[0]

        return values


def parse_gstreamer_taglist(tags):
    """Takes a GStreamer taglist and returns a dict containing only
    numeric and unicode values and str keys."""

    merged = {}
    for key in tags.keys():
        value = tags[key]
        # extended-comment sometimes contains a single vorbiscomment or
        # a list of them ["key=value", "key=value"]
        if key == "extended-comment":
            if not isinstance(value, list):
                value = [value]
            for val in value:
                if not isinstance(val, str):
                    continue
                split = val.split("=", 1)
                sub_key = split[0]
                val = split[-1]
                if sub_key in merged:
                    sub_val = merged[sub_key]
                    if not isinstance(sub_val, str):
                        continue
                    if val not in sub_val.split("\n"):
                        merged[sub_key] += "\n" + val
                else:
                    merged[sub_key] = val
        elif isinstance(value, Gst.DateTime):
            value = value.to_iso8601_string()
            merged[key] = value
        else:
            if isinstance(value, int | float):
                merged[key] = value
                continue

            if isinstance(value, bytes):
                value = decode(value)

            if not isinstance(value, str):
                value = str(value)

            if key in merged:
                merged[key] += "\n" + value
            else:
                merged[key] = value

    return merged


def bin_debug(elements, depth=0, lines=None):
    """Takes a list of gst.Element that are part of a prerolled pipeline, and
    recursively gets the children and all caps between the elements.

    Returns a list of text lines suitable for printing.
    """

    from quodlibet.util.dprint import Colorise

    if lines is None:
        lines = []
    else:
        lines.append(" " * (depth - 1) + "\\")

    for _i, elm in enumerate(elements):
        for pad in iter_to_list(elm.iterate_sink_pads):
            caps = pad.get_current_caps()
            if caps:
                lines.append("{}| {}".format(" " * depth, caps.to_string()))
        name = elm.get_name()
        cls = Colorise.blue(type(elm).__name__.split(".", 1)[-1])
        lines.append("{}|-{} ({})".format(" " * depth, cls, name))

        if isinstance(elm, Gst.Bin):
            children = reversed(iter_to_list(elm.iterate_sorted))
            bin_debug(children, depth + 1, lines)

    return lines
