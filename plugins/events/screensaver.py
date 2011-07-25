# Copyright 2011 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import gtk
import dbus

from quodlibet.plugins.events import EventPlugin

class BaseScreensaver(object):
    __bus_name = "org.gnome.ScreenSaver"
    __interface = "org.gnome.ScreenSaver"
    __path = "/org/gnome/ScreenSaver"

    __bus = None

    def _get_bus(self):
        self.__bus = self.__bus or dbus.Bus(dbus.Bus.TYPE_SESSION)
        return self.__bus

    def _get_object(self):
        try: obj = self._get_bus().get_object(self.__bus_name,  self.__path)
        except dbus.DBusException: return
        return obj

    def disabled(self):
        self.__bus = None

    def add_signal_receiver(self, signal, callback):
        self._get_bus().add_signal_receiver(callback, signal,
            self.__interface, self.__bus_name, self.__path)

class ScreensaverInhibit(BaseScreensaver, EventPlugin):
    PLUGIN_ID = "screensaver_inhibit"
    PLUGIN_NAME = _("Inhibit Screensaver")
    PLUGIN_DESC = _("Prevent the GNOME screensaver from activating while"
        " a song is playing.")
    PLUGIN_ICON = gtk.STOCK_STOP
    PLUGIN_VERSION = "0.1"

    __cookie = None

    def enabled(self):
        from quodlibet.player import playlist as player
        if not player.paused:
            self.plugin_on_unpaused()

    def disabled(self):
        from quodlibet.player import playlist as player
        if not player.paused:
            self.plugin_on_paused()
        BaseScreensaver.disabled(self)

    def plugin_on_unpaused(self):
        obj = self._get_object()
        if obj:
            self.__cookie = obj.Inhibit("Quod Libet", "Quod Libet plugin")

    def plugin_on_paused(self):
        obj = self._get_object()
        if obj and self.__cookie:
            obj.UnInhibit(self.__cookie)
            self.__cookie = None

class ScreensaverPause(BaseScreensaver, EventPlugin):
    PLUGIN_ID = "screensaver_pause"
    PLUGIN_NAME = _("Screensaver Pause")
    PLUGIN_DESC = _("Pause while the GNOME screensaver is active.")
    PLUGIN_ICON = gtk.STOCK_MEDIA_PAUSE
    PLUGIN_VERSION = "0.1"

    __was_paused = False

    def __screensaver_changed(self, active):
        from quodlibet.player import playlist as player
        if active:
            self.__was_paused = player.paused
            player.paused = True
        elif not self.__was_paused:
            player.paused = False

    def enabled(self):
        self.add_signal_receiver("ActiveChanged", self.__screensaver_changed)
