import re

from gi.repository import Gtk, GObject

from quodlibet.plugins.editing import RenameFilesPlugin, TagsFromPathPlugin

class RegExpSub(Gtk.HBox, RenameFilesPlugin, TagsFromPathPlugin):
    PLUGIN_ID = "Regex Substitution"
    PLUGIN_NAME = _("Regex Substitution")
    PLUGIN_DESC = _("Allow arbitrary regex substitutions (s///) when "
                    "tagging or renaming files.")
    PLUGIN_ICON = Gtk.STOCK_FIND_AND_REPLACE
    PLUGIN_VERSION = "1"

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ())
        }
    active = True

    def __init__(self):
        super(RegExpSub, self).__init__()
        self._from = Gtk.Entry()
        self._to = Gtk.Entry()
        self.pack_start(Gtk.Label("s/"), True, True, 0)
        self.pack_start(self._from, True, True, 0)
        self.pack_start(Gtk.Label("/"), True, True, 0)
        self.pack_start(self._to, True, True, 0)
        self.pack_start(Gtk.Label("/"), True, True, 0)

        self._from.connect_object('changed', self.emit, 'changed')
        self._to.connect_object('changed', self.emit, 'changed')

    def filter(self, orig_or_tag, value):
        fr = self._from.get_text().decode('utf-8')
        to = self._to.get_text().decode('utf-8')
        try: return re.sub(fr, to, value)
        except: return value
