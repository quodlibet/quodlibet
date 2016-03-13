# -*- coding: utf-8 -*-
import os
import sys

from quodlibet.qltk import Icons

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

from gi.repository import Gtk, GObject

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
        super(Kakasi, self).__init__(
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
        except None:
            return value
        line = ("kakasi -isjis -osjis -Ha -Ka -Ja -Ea -ka -s")
        w, r = os.popen2(line.split())
        w.write(data)
        w.close()
        try:
            return r.read().decode('shift-jis').strip().split("\n")
        except:
            return values


if not iscommand("kakasi"):
    from quodlibet import plugins
    raise plugins.PluginImportException(
        _("Couldn't find the 'Kanji Kana Simple Inverter' (kakasi)."))
