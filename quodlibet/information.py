import gtk
from util import escape

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

class SongInformation(gtk.Window):
    __windows = {}
    
    def __new__(klass, uri):
        win = klass.__windows.get(uri, None)
        if win is None:
            win = gtk.Window.__new__(klass)
            win.__real_init(uri)
            klass.__windows[uri] = win
            win.connect_object('destroy', klass.__windows.__delitem__, uri)
        return win

    def __init__(self, uri): self.present()

    def __real_init(self, uri):
        gtk.Window.__init__(self)
        self.set_border_width(12)
        vb = gtk.VBox(spacing=6)
        vb.pack_start(gtk.Label("What, you were expecting something?"))
        vb.pack_start(gtk.Label("You're at %s" % uri))
        vb.pack_start(FakeHref("ql://elsewhere", "Visit elsewhere"))
        self.add(vb)
        self.child.show_all()
        self.show()
