# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import config
from quodlibet import util
from quodlibet.plugins._modulescanner import ModuleScanner


__all__ = ["PluginImportException", "PluginManager"]


class PluginImportException(Exception):
    desc = ""

    def __init__(self, desc):
        super(PluginImportException, self).__init__()
        self.desc = desc


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
                        handler.plugin_enable(plugin)
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
