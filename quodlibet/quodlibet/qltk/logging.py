import gtk

import quodlibet.util.logging

from quodlibet import qltk

class LoggingWindow(qltk.Window):
    def __init__(self):
        super(qltk.Window, self).__init__()
        self.set_default_size(400, 400)
        self.set_title(_("Output Log"))
        self.set_border_width(12)
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
        self.add(notebook)

        self.show_all()

