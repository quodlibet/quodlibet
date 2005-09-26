import os
import gtk
import urllib
from util import escape

__windows = {}
class FakeHref(gtk.Button):
    def __init__(self, url, text):
        gtk.Button.__init__(self, use_underline=False)
        l = gtk.Label()
        l.set_markup("<u>%s</u>" % escape(text))
        self.set_relief(gtk.RELIEF_NONE)
        self.set_border_width(0)
        self.set_focus_on_click(False) 
        self.add(l)
        self.connect_object('clicked', SongInformation, url)

def SongInformation(uri):
    win = __windows.get(uri, None)
    if win is None:
        type, string = urllib.splittype(uri)
        if type == "file": win = FileInformation(uri)
        else: raise ValueError("Unknown URI scheme: %s" % type)
        __windows[uri] = win
        win.connect_object('destroy', __windows.__delitem__, uri)
    else: win.present()
    return win

class FileInformation(gtk.Window):
    def __init__(self, uri):
        gtk.Window.__init__(self)
        filename = os.path.realpath(urllib.url2pathname(uri))
        self.set_border_width(12)
        vb = gtk.VBox(spacing=6)
        vb.pack_start(gtk.Label("What, you were expecting something?"))
        vb.pack_start(gtk.Label("You're at %s" % uri))
        vb.pack_start(FakeHref("ql://elsewhere", "Visit elsewhere"))
        self.add(vb)
        self.child.show_all()
        self.show()
