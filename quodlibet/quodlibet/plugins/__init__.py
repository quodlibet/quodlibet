# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from quodlibet import config
from quodlibet import util
from quodlibet.util.modulescanner import ModuleScanner
from quodlibet.util.dprint import print_d
from quodlibet.qltk.ccb import ConfigCheckButton


def init(folders=None, disable_plugins=False):
    """folders: list of paths to look for plugins
    disable_plugins: disables all plugins, but does not forget which
    plugins are enabled.
    """
    if disable_plugins:
        folders = []
    manager = PluginManager.instance = PluginManager(folders)
    return manager


def quit():
    PluginManager.instance.save()
    PluginManager.instance.quit()
    PluginManager.instance = None


class PluginImportException(Exception):
    desc = ""
    platforms = None

    def __init__(self, desc, platforms=None):
        """platforms is a list of platform names where this error should be
        shown. In case it is None it will always be shown."""
        super(PluginImportException, self).__init__()
        self.desc = desc
        self.platforms = platforms

    def should_show(self):
        """If the error should be shown on the current platform"""
        if self.platforms is not None:
            sw = lambda x: sys.platform.startswith(x)
            if sum(map(sw, self.platforms)):
                return True
            return False
        return True

def migrate_old_config():
    active = []
    old_keys = ["songsmenuplugins", "eventplugins", "editingplugins",
                "playorderplugins"]
    for key in old_keys:
        key = "active_" + key
        try:
            active.extend(config.get("plugins", key).splitlines())
        except config.error:
            pass
        else:
            config._config.remove_option("plugins", key)

    if active:
        config.set("plugins", "active_plugins", "\n".join(active))


def list_plugins(module):
    """Return all objects of the module that satisfy the basic
    plugin needs: id, name and don't start with '_'

    If '__all__' is defined, only plugins in '__all__' will be loaded.
    """

    try: objs = [getattr(module, attr) for attr in module.__all__]
    except AttributeError:
        objs = [getattr(module, attr) for attr in vars(module)
                if not attr.startswith("_")]

    ok = []
    for obj in objs:
        if hasattr(obj, "PLUGIN_ID"):
            if not hasattr(obj, "PLUGIN_NAME"):
                obj.PLUGIN_NAME = obj.PLUGIN_ID
            ok.append(obj)

    return ok


class PluginManager(object):
    """
    The manager takes care of plugin loading/reloading. Interested plugin
    handlers can register them self to get called when plugins get enabled
    or disabled.

    Plugins get exposed when at least one handler shows interest
    in them (by returning True in the handle method).

    Plugins need to define PLUGIN_ID, PLUGIN_NAME attributes to get loaded.

    Plugins that have a true PLUGIN_INSTANCE attribute get instantiated on
    enable and the enabled/disabled methods get called.

    If plugin handlers want a plugin instance, they have to call
    get_instance to get a singleton.

    handlers need to implement the following methods:

        handler.plugin_handle(plugin)
            Needs to return True if the handler should be called
            whenever the plugin's enabled status changes.

        handler.plugin_enable(plugin, instance)
            Gets called if the plugin gets enabled.
            2nd parameter is an instance of the plugin or None

        handler.plugin_disable(plugin)
            Gets called if the plugin gets disabled.
            Should remove all references.
    """

    CONFIG_SECTION = "plugins"
    CONFIG_OPTION = "active_plugins"

    instance = None # default instance

    def __init__(self, folders=None):
        """folders is a list of paths that will be scanned for plugins.
        Plugins in later paths will be preferred if they share a name.
        """

        super(PluginManager, self).__init__()

        if folders is None:
            folders = []

        self.__scanner = ModuleScanner(folders)
        self.__modules = {}     # name: module
        self.__plugins = {}     # module: [plugin, ..]
        self.__handlers = {}    # plugins: [handler, ..]
        self.__instance = {}    # plugin: instance
        self.__list = []        # handler list
        self.__enabled = set()  # (possibly) enabled plugin IDs

        self.__restore()

    def rescan(self):
        """Scan for plugin changes or to initially load all plugins"""

        print_d("Rescanning..")

        removed, added = self.__scanner.rescan()
        modules = self.__scanner.modules

        # remember IDs of enabled plugin that get reloaded, so we can enable
        # them again
        reload_ids = []
        for name in removed:
            if name not in added:
                continue
            mod = self.__modules[name]
            for plugin in self.__plugins[mod]:
                if self.enabled(plugin):
                    reload_ids.append(plugin.PLUGIN_ID)

        for name in removed:
            # share the namespace with ModuleScanner for now
            self.__remove_module(name)

        # restore enabled state
        self.__enabled.update(reload_ids)

        for name in added:
            module = modules[name]
            self.__add_module(name, module)

        print_d("Rescanning done.")

    @property
    def _modules(self):
        return self.__scanner.modules.itervalues()

    @property
    def plugins(self):
        """Returns a list of plugin classes or instances"""

        items = self.__handlers.items()
        return [self.get_instance(p) or p for (p,h) in items if h]

    def get_instance(self, plugin):
        """"Returns a possibly shared instance of the plugin class"""

        if not getattr(plugin, "PLUGIN_INSTANCE", False):
            return

        if plugin not in self.__instance:
            try:
                obj = plugin()
            except:
                util.print_exc()
                return
            self.__instance[plugin] = obj
        return self.__instance[plugin]

    def register_handler(self, handler):
        print_d("Registering handler: %r" % type(handler).__name__)
        self.__list.append(handler)
        for plugins in self.__plugins.itervalues():
            for plugin in plugins:
                if not handler.plugin_handle(plugin):
                    continue
                if self.__handlers.get(plugin):
                    self.__handlers[plugin].append(handler)
                    if self.enabled(plugin):
                        obj = self.get_instance(plugin)
                        handler.plugin_enable(plugin, obj)
                else:
                    self.__handlers[plugin] = [handler]
                    if self.enabled(plugin):
                        self.enable(plugin, True, force=True)

    def save(self):
        print_d("Saving plugins: %d active" % len(self.__enabled))
        config.set(self.CONFIG_SECTION,
                   self.CONFIG_OPTION,
                   "\n".join(self.__enabled))

    def enabled(self, plugin):
        """Returns if the plugin is enabled. Also takes an instance."""

        if type(plugin) in self.__handlers:
            plugin = type(plugin)

        return plugin.PLUGIN_ID in self.__enabled

    def enable(self, plugin, status, force=False):
        """Enable or disable a plugin. Also takes an instance."""

        if type(plugin) in self.__handlers:
            plugin = type(plugin)

        if not force and self.enabled(plugin) == bool(status):
            return

        if not status:
            print_d("Disable %r" % plugin.PLUGIN_ID)
            for handler in self.__handlers[plugin]:
                handler.plugin_disable(plugin)
            self.__enabled.discard(plugin.PLUGIN_ID)
            instance = self.__instance.get(plugin)
            if instance and hasattr(instance, "disabled"):
                try:
                    instance.disabled()
                except Exception:
                    util.print_exc()
        else:
            print_d("Enable %r" % plugin.PLUGIN_ID)
            obj = self.get_instance(plugin)
            if obj and hasattr(obj, "enabled"):
                try:
                    obj.enabled()
                except Exception:
                    util.print_exc()
            for handler in self.__handlers[plugin]:
                handler.plugin_enable(plugin, obj)
            self.__enabled.add(plugin.PLUGIN_ID)

    @property
    def failures(self):
        errors = {}
        for (name, (exc, text)) in self.__scanner.failures.iteritems():
            if isinstance(exc, PluginImportException):
                if not exc.should_show():
                    continue
                errors[name] = [exc.desc]
            else:
                errors[name] = text
        return errors

    def quit(self):
        """Disable plugins and tell all handlers to clean up"""
        for name in self.__modules.keys():
            self.__remove_module(name)

    def __remove_module(self, name):
        module = self.__modules.pop(name)
        plugins = self.__plugins.pop(module)

        for plugin in plugins:
            if self.__handlers.get(plugin):
                self.enable(plugin, False)
            self.__handlers.pop(plugin, None)

    def __add_module(self, name, module):
        self.__modules[name] = module
        plugins = list_plugins(module)
        self.__plugins[module] = plugins

        for plugin in plugins:
            handlers = []
            for handler in self.__list:
                if handler.plugin_handle(plugin):
                    handlers.append(handler)
            if handlers:
                self.__handlers[plugin] = handlers
                if self.enabled(plugin):
                    self.enable(plugin, True, force=True)

    def __restore(self):
        migrate_old_config()
        active = config.get(self.CONFIG_SECTION,
                            self.CONFIG_OPTION, "").splitlines()

        self.__enabled.update(active)
        print_d("Restoring plugins: %d" % len(self.__enabled))
        for plugin, handlers in self.__handlers.iteritems():
            if self.enabled(plugin):
                self.enable(plugin, True, force=True)

PM = PluginManager


class PluginConfigMixin(object):
    """
    Mixin for storage and editing of plugin config in a standard way
    Will use `CONFIG_SECTION`, if defined, for storing config, otherwise,
    it will base the keys on `PLUGIN_ID`.
    """

    @classmethod
    def _config_key(cls, name):
        try:
            prefix = cls.CONFIG_SECTION
        except AttributeError:
            prefix = cls.PLUGIN_ID.lower().replace(" ", "_")
        return "%s_%s" % (prefix, name)

    @classmethod
    def config_get(cls, name, default=""):
        """Gets a config string value for this plugin"""
        return config.get(PM.CONFIG_SECTION, cls._config_key(name), default)

    @classmethod
    def config_set(cls, name, value):
        """Saves a config string value for this plugin"""
        try:
            config.set(PM.CONFIG_SECTION, cls._config_key(name), value)
        except config.error:
            print_d("Couldn't set config item '%s' to %r" % (name, value))

    @classmethod
    def config_get_bool(cls, name, default=False):
        """Gets a config boolean for this plugin"""
        return config.getboolean(PM.CONFIG_SECTION, cls._config_key(name),
            default)

    def config_entry_changed(self, entry, key):
        """React to a change in an gtk.Entry (by saving it to config)"""
        if entry.get_property('sensitive'):
            self.config_set(key, entry.get_text())

    @classmethod
    def ConfigCheckButton(cls, label, name, default=False):
        """
        Create a new `ConfigCheckButton` for `name`, pre-populated correctly
        """
        option = cls._config_key(name)
        try:
            config.getboolean(PM.CONFIG_SECTION, option)
        except config.error:
            cls.config_set(name, default)
        return ConfigCheckButton(label, PM.CONFIG_SECTION,
            option, populate=True)
