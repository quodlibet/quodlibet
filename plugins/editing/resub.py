import re
import gtk, gobject
from quodlibet.plugins.editing import RenameFilesPlugin, TagsFromPathPlugin

class RegExpSub(gtk.HBox, RenameFilesPlugin, TagsFromPathPlugin):
    PLUGIN_ID = "Regex Substitution"
    PLUGIN_NAME = _("Regex Substitution")
    PLUGIN_DESC = _("Allow arbitrary regex substitutions (s///) when "
                    "tagging or renaming files.")
    PLUGIN_ICON = gtk.STOCK_FIND_AND_REPLACE
    PLUGIN_VERSION = "1"

    __gsignals__ = {
        "changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }
    active = True

    def __init__(self):
        super(RegExpSub, self).__init__()
        self._from = gtk.Entry()
        self._to = gtk.Entry()
        self.pack_start(gtk.Label("s/"), expand=False)
        self.pack_start(self._from)
        self.pack_start(gtk.Label("/"), expand=False)
        self.pack_start(self._to)
        self.pack_start(gtk.Label("/"), expand=False)

        self._from.connect_object('changed', self.emit, 'changed')
        self._to.connect_object('changed', self.emit, 'changed')

    def filter(self, orig_or_tag, value):
        fr = self._from.get_text().decode('utf-8')
        to = self._to.get_text().decode('utf-8')
        try: return re.sub(fr, to, value)
        except: return value
