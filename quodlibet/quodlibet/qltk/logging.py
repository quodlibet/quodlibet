from gi.repository import Gtk

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
            view = Gtk.TextView()
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            sw.set_shadow_type(Gtk.ShadowType.IN)
            sw.add(view)
            buffer = view.get_buffer()
            buffer.set_text(text)
            notebook.append_page(sw, logname)

        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close.connect_object('clicked', lambda x: x.destroy(), self)
        button_box = Gtk.HButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.END)
        button_box.pack_start(close, True, True, 0)

        vbox = Gtk.VBox(spacing=12)
        vbox.pack_start(notebook, True, True, 0)
        vbox.pack_start(button_box, False, True, 0)
        self.add(vbox)

        self.show_all()
