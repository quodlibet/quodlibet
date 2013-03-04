# Copyright 2009-2011 Steven Robertson, Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GLib, Gst

from quodlibet import util
from quodlibet import config
from quodlibet.plugins.gstelement import GStreamerPlugin
from quodlibet.plugins import PluginManager


def link_many(elements):
    last = None
    for element in elements:
        if last:
            if not Gst.Element.link(last, element):
                return False
        last = element
    return True


def unlink_many(elements):
    last = None
    for element in elements:
        if last:
            if not Gst.Element.unlink(last, element):
                return False
        last = element
    return True


def recurse_bin(element):
    objects = [element]

    iter_ = element.iterate_recurse()
    while 1:
        status, value = iter_.next()
        if status == Gst.IteratorResult.OK:
            objects.append(value)
        else:
            break
    return objects


def GStreamerSink(pipeline):
    """Try to create a GStreamer pipeline:
    * Try making the pipeline (defaulting to gconfaudiosink or
      autoaudiosink on Windows).
    * If it fails, fall back to autoaudiosink.
    * If that fails, return None

    Returns the pipeline's description and a list of disconnected elements."""

    if not pipeline and not Gst.ElementFactory.find('gconfaudiosink'):
        pipeline = "autoaudiosink"
    elif not pipeline or pipeline == "gconf":
        pipeline = "gconfaudiosink profile=music"

    try: pipe = [Gst.parse_launch(element) for element in pipeline.split('!')]
    except GLib.GError:
        print_w(_("Invalid GStreamer output pipeline, trying default."))
        try: pipe = [Gst.parse_launch("autoaudiosink")]
        except GLib.GError: pipe = None
        else: pipeline = "autoaudiosink"

    if pipe:
        # In case the last element is linkable with a fakesink
        # it is not an audiosink, so we append the default pipeline
        fake = Gst.ElementFactory.make('fakesink', None)
        if link_many([pipe[-1], fake]):
            unlink_many([pipe[-1], fake])
            default, default_text = GStreamerSink("")
            if default:
                return pipe + default, pipeline + " ! "  + default_text
    else:
        print_w(_("Could not create default GStreamer pipeline."))

    return pipe, pipeline


class GStreamerPluginHandler(object):
    def init_plugins(self):
        PluginManager.instance.register_handler(self)

    def __init__(self):
        self.__plugins = []
        self.__elements = {}

    def __get_plugin_element(self, plugin):
        """Setup element and cache it, so we can pass the linked/active
           one to the plugin for live updates"""
        if plugin not in self.__elements:
            element = plugin.setup_element()
            if not element:
                return
            plugin.update_element(element)
            self.__elements[plugin] = element
        return self.__elements[plugin]

    def plugin_handle(self, plugin):
        try:
            ok = issubclass(plugin, GStreamerPlugin) and plugin.setup_element()
        except Exception:
            util.print_exc()
            ok = False

        if ok:
            plugin._handler = self
        return ok

    def plugin_enable(self, plugin, obj):
        self.__plugins.append(plugin)
        self._rebuild_pipeline()

    def plugin_disable(self, plugin):
        try: self.__elements.pop(plugin)
        except KeyError: pass
        self.__plugins.remove(plugin)
        self._rebuild_pipeline()

    def _remove_plugin_elements(self):
        """Call on pipeline destruction to remove element references"""
        self.__elements.clear()

    def _get_plugin_elements(self):
        """Return a list of plugin elements"""
        for plugin in self.__plugins:
            self.__get_plugin_element(plugin)

        items = sorted(self.__elements.items(),
                       key=lambda x: x[0].priority,
                       reverse=True)
        return [p[1] for p in items]

    def _queue_update(self, plugin):
        # If we have an instance, apply settings, otherwise
        # this will be done on creation
        if plugin in self.__elements:
            plugin.update_element(self.__elements[plugin])

def parse_gstreamer_taglist(tags):
    """Takes a GStreamer taglist and returns a dict containing only
    numeric and unicode values and str keys."""

    merged = {}
    for key in tags.keys():
        value = tags[key]
        # extended-comment sometimes containes a single vorbiscomment or
        # a list of them ["key=value", "key=value"]
        if key == "extended-comment":
            if not isinstance(value, list):
                value = [value]
            for val in value:
                if not isinstance(val, unicode): continue
                split = val.split("=", 1)
                sub_key = util.decode(split[0])
                val = split[-1]
                if sub_key in merged:
                    if val not in merged[sub_key].split("\n"):
                        merged[sub_key] += "\n" + val
                else:
                    merged[sub_key] = val
        elif isinstance(value, gst.Date):
                try: value = u"%d-%d-%d" % (value.year, value.month, value.day)
                except (ValueError, TypeError): continue
                merged[key] = value
        elif isinstance(value, list):
            # there are some lists for id3 containing gst.Buffer (binary data)
            continue
        else:
            if isinstance(value, str):
                value = util.decode(value)

            if not isinstance(value, unicode) and \
                not isinstance(value, (int, long, float)):
                value = unicode(value)

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

    for i, elm in enumerate(elements):
        for pad in elm.pads():
            if i and pad.get_direction() == gst.PAD_SINK:
                caps = pad.get_negotiated_caps()
                if caps is not None:
                    d = dict(caps[0])
                    d = sorted([(s[0], repr(s[1])) for s in d.items()])
                    d = [("format", caps[0].get_name())] + d
                    d = ", ".join(map(":".join, d))
                    lines.append("%s| %s" % (" " * depth, d))
                    break
        name = elm.get_name()
        cls = Colorise.blue(type(elm).__name__.split(".", 1)[-1])
        lines.append("%s|-%s (%s)" % (" " * depth, cls, name))

        if isinstance(elm, gst.Bin):
            children = reversed(list(elm.sorted()))
            bin_debug(children, depth + 1, lines)

    return lines
