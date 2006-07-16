import os, gtk, gobject
import util
from plugins.editing import RenameFilesPlugin

class Kakasi(RenameFilesPlugin, gtk.CheckButton):
    PLUGIN_ID = "Kana/Kanji Simple Inverter"
    PLUGIN_NAME = _("Kana/Kanji Simple Inverter")
    PLUGIN_DESC = _("Convert kana/kanji to romaji before renaming.")
    PLUGIN_ICON = gtk.STOCK_CONVERT
    PLUGIN_VERSION = "1"

    __gsignals__ = {
        "preview": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }
    def __init__(self):
        super(Kakasi, self).__init__("Romanize _Japanese text")
        self.connect_object('toggled', self.emit, 'preview')

    active = property(lambda s: s.get_active())

    # Use filter list rather than filter to avoid starting a new process
    # for each filename.
    def filter_list(self, originals, values):
        value = "\n".join(values)
        try: data = value.encode('shift-jis', 'replace')
        except None: return value
        line = ("kakasi -isjis -osjis -Ha -Ka -Ja -Ea -ka -s")
        w, r = os.popen2(line.split())
        w.write(data)
        w.close()
        try: return r.read().decode('shift-jis').strip().split("\n")
        except: return values

if not util.iscommand("kakasi"): del(Kakasi)
