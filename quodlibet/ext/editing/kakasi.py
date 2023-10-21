# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import subprocess

from quodlibet.qltk import Icons

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

from gi.repository import Gtk, GObject

from quodlibet import _
from quodlibet.plugins.editing import RenameFilesPlugin
from quodlibet.util.path import iscommand
from quodlibet.util import connect_obj


class Kakasi(RenameFilesPlugin, Gtk.CheckButton):
    PLUGIN_ID = "Kana/Kanji Simple Inverter"
    PLUGIN_NAME = _("Kana/Kanji Simple Inverter")
    PLUGIN_DESC = _("Converts kana/kanji to romaji before renaming.")
    PLUGIN_ICON = Icons.EDIT_FIND_REPLACE

    __gsignals__ = {
        "preview": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):
        super().__init__(
            _("Romanize _Japanese text"), use_underline=True)
        connect_obj(self, 'toggled', self.emit, 'preview')

    @property
    def active(self):
        return self.get_active()

    # Use filter list rather than filter to avoid starting a new process
    # for each filename.
    def filter_list(self, originals, values):
        value = "\n".join(values)
        try:
            data = value.encode('shift-jis', 'replace')
        except UnicodeEncodeError:
            return values

        proc = subprocess.Popen(
            ["kakasi", "-isjis", "-osjis", "-Ha", "-Ka", "-Ja",
             "-Ea", "-ka", "-s"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
        result = proc.communicate(data)[0]

        try:
            return result.decode('shift-jis').strip().split("\n")
        except Exception:
            return values


if not iscommand("kakasi"):
    from quodlibet import plugins
    raise plugins.PluginImportException(
        _("Couldn't find the 'Kanji Kana Simple Inverter' (kakasi)."))
