# Copyright 2009-2011 Steven Robertson, Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import pygst
pygst.require("0.10")

import gtk
import gst
import gobject

from quodlibet import util
from quodlibet import config
from quodlibet.plugins.gstelement import GStreamerPlugin
from quodlibet.plugins import PluginManager


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
    except gobject.GError:
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


class DeviceComboBox(gtk.ComboBox):
    """A ComboBox that is prefilled with all possible devices
    of the pipeline."""

    DEVICE, NAME = range(2)

    def __init__(self):
        model = gtk.ListStore(str, str)
        super(DeviceComboBox, self).__init__(model)

        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        self.set_cell_data_func(cell, self.__draw_device)

        self.__sig = self.connect_object(
            'changed', self.__device_changed, model)

        self.refresh()

    def refresh(self):
        """Reread the current pipeline config and refresh the list"""

        self.handler_block(self.__sig)

        model = self.get_model()
        model.clear()
        self.__fill_model(model)

        if not len(model):
            self.handler_unblock(self.__sig)
            # Translators: Unknown audio output device.
            model.append(row=["", _("Unknown")])
            self.set_active(0)
            self.set_sensitive(False)
            return

        self.set_sensitive(True)

        # Translators: Default audio output device.
        model.insert(0, row=["", _("Default")])

        dev = config.get("player", "gst_device")
        for row in model:
            if row[self.DEVICE] == dev:
                self.set_active_iter(row.iter)
                break

        self.handler_unblock(self.__sig)

        # If no dev was found, change to default so the config gets reset
        if self.get_active() == -1:
            self.set_active(0)

    def __fill_model(self, model):
        pipeline = config.get("player", "gst_pipeline")
        pipeline, name = GStreamerSink(pipeline)
        if not pipeline:
            return

        sink = pipeline[-1]
        sink.set_state(gst.STATE_READY)

        base_sink = sink

        if isinstance(sink, gst.Bin):
            sink = list(sink.recurse())[-1]

        if hasattr(sink, "probe_property_name"):
            sink.probe_property_name("device")
            devices = sink.probe_get_values_name("device")

            for dev in devices:
                sink.set_property("device", dev)
                model.append(row=[dev, sink.get_property("device-name")])

        base_sink.set_state(gst.STATE_NULL)
        base_sink.get_state()

    def __device_changed(self, model):
        row = model[self.get_active_iter()]
        config.set("player", "gst_device", row[self.DEVICE])

    def __draw_device(self, column, cell, model, it):
        cell.set_property('text', model[it][self.NAME])


def set_sink_device(sink):
    # Set the device (has to be in ready state for gconfsink etc.)
    device = config.get("player", "gst_device")
    if not device:
        return

    # get the real sink (gconfaudiosink)
    if isinstance(sink, gst.Bin):
        sink = list(sink.recurse())[-1]

    for prop in ["device", "device-name"]:
        if not hasattr(sink.props, prop):
            return

    # set the device, if device-name returns None,
    # the device isn't valid, so reset
    sink.set_property("device", device)
    if sink.get_property("device-name") is None:
        sink.set_property("device", None)

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

    from quodlibet.util.dprint import COLOR

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
        cls = COLOR.Blue(type(elm).__name__.split(".", 1)[-1])
        lines.append("%s|-%s (%s)" % (" " * depth, cls, name))

        if isinstance(elm, gst.Bin):
            children = reversed(list(elm.sorted()))
            bin_debug(children, depth + 1, lines)

    return lines
