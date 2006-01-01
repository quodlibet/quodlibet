import sre
import gtk, gobject
from plugins.editing import RenameFilesPlugin

class RegExpSub(RenameFilesPlugin, gtk.HBox):
    active = True

    __gsignals__ = {
        "preview": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }
    def __init__(self):
        super(RegExpSub, self).__init__()
        self.__from = gtk.Entry()
        self.__to = gtk.Entry()
        self.pack_start(gtk.Label("s/"))
        self.pack_start(self.__from)
        self.pack_start(gtk.Label("/"))
        self.pack_start(self.__to)
        self.pack_start(gtk.Label("/"))

        self.__from.connect_object('changed', self.emit, 'preview')
        self.__to.connect_object('changed', self.emit, 'preview')

    def filter(self, value):
        fr = self.__from.get_text().decode('utf-8')
        to = self.__to.get_text().decode('utf-8')
        try: return sre.sub(fr, to, value)
        except: return value
gobject.type_register(RegExpSub)
