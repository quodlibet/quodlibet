# -*- coding: utf-8 -*-
# Copyright 2018 David Morris
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository            import Gtk, Pango
from quodlibet                import _
from quodlibet                import app
from quodlibet                import qltk
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins        import PluginConfigMixin
from quodlibet.qltk           import Icons
from quodlibet.qltk.ccb       import ConfigCheckButton

class StopOnPause(EventPlugin, PluginConfigMixin):

    PLUGIN_ID   = "StopOnPause"
    PLUGIN_NAME = _("Stop On Pase")
    PLUGIN_ICON = Icons.MEDIA_PLAYBACK_PAUSE
    PLUGIN_DESC = _("This plugin changes Pause to Stop/Play/Seek.\n\n" \
                    "This behavior is useful if Quod Libet fails to switch " \
                    "audio devices when a new audio device is added to the " \
                    "system (Bluetooth speaker, USB DAC, etc).\n\n" \
                    "If the option for 'Only Seekable Sources' " \
                    "is not checked, this plugin will ensure the position in the " \
                    "current source is maintained.  Otherwise, playback will " \
                    "be left stopped and must restart from the begining.")

    _CFG_SEEKABLE_ONLY = 'seekable_only'

    __enabled    = False
    __restarting = False

    def enabled(self):
        self.__enabled = True

    def disabled(self):
        self.__enabled = False

    def plugin_on_paused(self):
        if self.__enabled:
            if not self.__restarting:
                onlySeekable = self.config_get_bool(self._CFG_SEEKABLE_ONLY)

                if (onlySeekable and app.player.seekable):
                    self.__restarting = True
                    position = app.player.get_position()
                    app.player.stop()
                    app.player.seek(position)
                    self.__restarting = False
                elif not onlySeekable:
                    self.__restarting = True

                    # Check if the stream is seekable before stopping!
                    isSeekable =  app.player.seekable:

                    app.player.stop()

                    if isSeekable:
                        position = app.player.get_position()
                        app.player.seek(position)

                    self.__restarting = False

    @classmethod
    def PluginPreferences(cls, window):
        # Plugin Options
        toggles = [
            (cls._CFG_SEEKABLE_ONLY, _("Only Seekable Sources")),
        ]

        vb = Gtk.VBox(spacing=10)
        vb.set_border_width(0)
        vb2 = Gtk.VBox(spacing=6)
        for key, label in toggles:
            ccb = ConfigCheckButton(label, 'plugins', cls._config_key(key))
            ccb.set_active(cls.config_get_bool(key))
            vb2.pack_start(ccb, True, True, 0)

        frame = qltk.Frame(label=_("Plugin Options"), child=vb2)
        vb.pack_start(frame, False, True, 0)

        vb.show_all()
        return vb
