# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

class GetStringDialog(gtk.Dialog):
    def __init__(
        self, parent, title, text, options=[], okbutton=gtk.STOCK_OPEN):
        super(GetStringDialog, self).__init__(title, parent)
        self.set_border_width(6)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         okbutton, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)

        box = gtk.VBox(spacing=6)
        lab = gtk.Label(text)
        box.set_border_width(6)
        lab.set_line_wrap(True)
        lab.set_justify(gtk.JUSTIFY_CENTER)
        box.pack_start(lab)

        if options:
            self._entry = gtk.combo_box_entry_new_text()
            for o in options: self._entry.append_text(o)
            self._val = self._entry.child
            box.pack_start(self._entry)
        else:
            self._val = gtk.Entry()
            box.pack_start(self._val)
        self.vbox.pack_start(box)
        self.child.show_all()

    def run(self, text=""):
        self.show()
        self._val.set_text(text)
        self._val.set_activates_default(True)
        self._val.grab_focus()
        resp = super(GetStringDialog, self).run()
        if resp == gtk.RESPONSE_OK:
            value = self._val.get_text()
        else: value = None
        self.destroy()
        return value
