# -*- coding: utf-8 -*-
# Copyright 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import signal

from gi.repository import Gtk

from quodlibet import _
from quodlibet import app
from quodlibet import print_d
from quodlibet import print_w
from quodlibet.plugins import PluginConfig
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Button
from quodlibet.qltk import ErrorMessage
from quodlibet.qltk import Icons
from quodlibet.qltk.entry import UndoEntry
from quodlibet.util import escape


class ProjectM(EventPlugin):
    """Launch external visualisations, e.g. via projectM

       Try this first (Ubuntu/Debian):
       sudo apt-get install projectm-pulseaudio
    """

    _config = PluginConfig(__name__)

    PLUGIN_ID = "visualisations"
    PLUGIN_NAME = _("Launch Visualisations")
    PLUGIN_ICON = Icons.IMAGE_X_GENERIC
    PLUGIN_DESC = _("Launch external visualisations.")

    DEFAULT_EXEC = 'projectM-pulseaudio'

    def __init__(self):
        self._pid = None

    def enabled(self):
        from gi.repository import GLib
        print_d("Starting %s" % self.PLUGIN_NAME)
        try:
            self._pid, fdin, fdout, fderr = GLib.spawn_async(
                argv=self.executable.split(),
                flags=GLib.SpawnFlags.SEARCH_PATH,
                standard_output=True,
                standard_input=True)
        except GLib.Error as e:
            msg = ((_("Couldn't run visualisations using '%s'") + " (%s)") %
                   (escape(self.executable), escape(e.message)))
            ErrorMessage(title=_("Error"), description=msg,
                         parent=app.window).run()
        else:
            # self._stdin = os.fdopen(fdin, mode='w')
            print_d("Launched with PID: %s" % self._pid)

    def disabled(self):
        if not self._pid:
            return
        print_d("Shutting down %s" % self.PLUGIN_NAME)
        try:
            os.kill(self._pid, signal.SIGTERM)
            os.kill(self._pid, signal.SIGKILL)
        except Exception as e:
            print_w("Couldn't shut down cleanly (%s)" % e)

    def PluginPreferences(self, *args):
        vbox = Gtk.VBox(spacing=12)

        label = Gtk.Label(label=_("Visualiser executable:"))

        def edited(widget):
            self.executable = widget.get_text()
        entry = UndoEntry()
        entry.connect('changed', edited)
        entry.set_text(self.executable)
        hbox = Gtk.HBox(spacing=6)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(entry, True, True, 0)
        vbox.pack_start(hbox, True, True, 0)

        def refresh_clicked(widget):
            self.disabled()
            self.enabled()
        refresh_button = Button(_("Reload"), Icons.VIEW_REFRESH)
        refresh_button.connect('clicked', refresh_clicked)
        vbox.pack_start(refresh_button, False, False, 0)
        return vbox

    @property
    def executable(self):
        return self._config.get('executable', self.DEFAULT_EXEC)

    @executable.setter
    def executable(self, value):
        self._config.set('executable', value)
