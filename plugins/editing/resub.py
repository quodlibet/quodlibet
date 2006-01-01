import sre
import gtk, gobject
from plugins.editing import RenameFilesPlugin, TagsFromPathPlugin

class RegExpSub(gtk.HBox):
    __gsignals__ = {
        "changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }
    def __init__(self):
        super(RegExpSub, self).__init__()
        self._from = gtk.Entry()
        self._to = gtk.Entry()
        self.pack_start(gtk.Label("s/"))
        self.pack_start(self._from)
        self.pack_start(gtk.Label("/"))
        self.pack_start(self._to)
        self.pack_start(gtk.Label("/"))

        self._from.connect_object('changed', self.emit, 'changed')
        self._to.connect_object('changed', self.emit, 'changed')
gobject.type_register(RegExpSub)

class RenameRESub(RenameFilesPlugin, RegExpSub):
    active = True

    def filter(self, value):
        fr = self._from.get_text().decode('utf-8')
        to = self._to.get_text().decode('utf-8')
        try: return sre.sub(fr, to, value)
        except: return value

class TagsFromPathRESub(TagsFromPathPlugin, RegExpSub):
    active = True

    def filter(self, tag, value):
        fr = self._from.get_text().decode('utf-8')
        to = self._to.get_text().decode('utf-8')
        try: return sre.sub(fr, to, value)
        except: return value
