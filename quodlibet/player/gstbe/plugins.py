# Copyright 2011 Christoph Reiter
#           2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet import util
from quodlibet.plugins import PluginManager, PluginHandler
from quodlibet.plugins.gstelement import GStreamerPlugin


class GStreamerPluginHandler(PluginHandler):
    def init_plugins(self):
        PluginManager.instance.register_handler(self)

    def __init__(self):
        self.__plugins = []
        self.__elements = {}

    def __get_plugin_element(self, plugin):
        """Setup element and cache it, so we can pass the linked/active
        one to the plugin for live updates"""
        if plugin not in self.__elements:
            element = None
            # make sure the plugin doesn't take us down
            try:
                element = plugin.setup_element()
            except Exception:
                util.print_exc()
            if not element:
                util.print_w(
                    _("GStreamer plugin '%(name)s' could not be initialized")
                    % {"name": plugin.PLUGIN_ID}
                )
                return
            plugin.update_element(element)
            self.__elements[plugin] = element
        return self.__elements[plugin]

    def plugin_handle(self, plugin):
        if not issubclass(plugin.cls, GStreamerPlugin):
            return False

        plugin.cls._handler = self
        return True

    def plugin_enable(self, plugin):
        self.__plugins.append(plugin.cls)
        self._rebuild_pipeline()

    def plugin_disable(self, plugin):
        try:
            self.__elements.pop(plugin.cls)
        except KeyError:
            pass
        self.__plugins.remove(plugin.cls)
        self._rebuild_pipeline()

    def _remove_plugin_elements(self):
        """Call on pipeline destruction to remove element references"""
        self.__elements.clear()

    def _get_plugin_elements(self):
        """Return a list of plugin elements"""
        for plugin in self.__plugins:
            self.__get_plugin_element(plugin)

        items = sorted(
            self.__elements.items(), key=lambda x: x[0].priority, reverse=True
        )
        return [p[1] for p in items]

    def _queue_update(self, plugin):
        # If we have an instance, apply settings, otherwise
        # this will be done on creation
        if plugin in self.__elements:
            plugin.update_element(self.__elements[plugin])
