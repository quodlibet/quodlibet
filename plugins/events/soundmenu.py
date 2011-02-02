# Copyright 2010 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import gtk
import dbus
import indicate

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
        self.server = server = indicate.indicate_server_ref_default()
        server.set_type("music.quodlibet")
        server.set_desktop_file("/usr/share/applications/quodlibet.desktop")
        server.show()

    def disabled(self):
        if self.server:
            self.server.hide()
            self.server = None

    def destroy(self):
        self.disabled()
