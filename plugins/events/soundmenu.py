# Copyright 2010 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import gtk
import dbus
try:
    import indicate
except ImportError:
    from quodlibet import plugins
    if not hasattr(plugins, "PluginImportException"): raise
    raise plugins.PluginImportException(
        "Couldn't find python bindings for libindicate (python-indicate).")

from quodlibet.plugins.events import EventPlugin

class SoundMenu(EventPlugin):
    PLUGIN_ID = "soundmenu"
    PLUGIN_NAME = _("Sound Menu Integration")
    PLUGIN_DESC = _("Lets you control Quod Libet using the "
        "'Ubuntu Sound Menu'.")
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.1"

    server = None

    def __check_mpris(self):
        bus = dbus.SessionBus()
        try:
            bus.get_object(
                "org.mpris.MediaPlayer2.quodlibet", "/org/mpris/MediaPlayer2")
        except dbus.DBusException:
            return False
        return True

    def __window_delete(self, win, event):
        win.hide()
        return True

    def PluginPreferences(self, parent):
        box = gtk.HBox()
        if not self.__check_mpris():
            box.set_border_width(6)
            label = gtk.Label()
            box.pack_start(label)
            label.set_markup(_("<b>You</b> need to <b>activate</b> "
                "the <i>\"MPRIS D-Bus support\"</i>\nplugin "
                "for this plugin to work."))
        return box

    def enabled(self):
        from quodlibet.widgets import main as window
        self.__sig = window.connect('delete-event', self.__window_delete)
        self.server = server = indicate.indicate_server_ref_default()
        server.set_type("music.quodlibet")
        server.set_desktop_file("/usr/share/applications/quodlibet.desktop")
        server.show()

    def disabled(self):
        from quodlibet.widgets import main as window
        window.disconnect(self.__sig)
        self.server.hide()
        self.server = None
