import gtk

import quodlibet.util.logging

from quodlibet import qltk

class LoggingWindow(qltk.Window):
    def __init__(self, parent=None):
        super(LoggingWindow, self).__init__()
        self.set_default_size(400, 400)
        self.set_title(_("Output Log"))
        self.set_border_width(12)
        self.set_transient_for(qltk.get_top_parent(parent))
        notebook = qltk.Notebook()

        for logname in quodlibet.util.logging.names():
            text = "\n".join(quodlibet.util.logging.contents(logname))
            view = gtk.TextView()
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.add(view)
            buffer = view.get_buffer()
            buffer.set_text(text)
            notebook.append_page(sw, logname)

        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect_object('clicked', lambda x: x.destroy(), self)
        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        button_box.pack_start(close)

        vbox = gtk.VBox(spacing=12)
        vbox.pack_start(notebook)
        vbox.pack_start(button_box, expand=False)
        self.add(vbox)

        self.show_all()

