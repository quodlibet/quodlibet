from quodlibet.plugins import PluginHandler, PluginManager
from quodlibet.plugins.gstappsrc import AppSrcPlugin

class GstAppSrcPluginHandler(PluginHandler):

    def __init__(self):
        self.__handlers = []

    def init_plugins(self):
        PluginManager.instance.register_handler(self)

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, AppSrcPlugin)

    def plugin_enable(self, plugin):
        self.__handlers.append(plugin.cls)

    def plugin_disable(self, plugin):
        self.__handlers.remove(plugin.cls)

    @property
    def handlers(self):
        return self.__handlers

    def get_handler_for_protocol(self, protocol):
        for handler in self.handlers:
            if handler.handles_protocol(protocol):
                print_d('got you a handler')
                return handler

        return None
