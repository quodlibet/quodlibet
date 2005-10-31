#!/usr/bin/env python

import gobject, gtk

class View(gtk.TreeView):
    def __init__(self, name):
        super(View, self).__init__()
        #self.add(gtk.ScrolledWindow())
        render = gtk.CellRendererText()
        col = gtk.TreeViewColumn(name, render, text=0)
        self.append_column(col)
        self.set_model(self._make_model())
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        targets = [("text/uri-list", gtk.TARGET_SAME_WIDGET, 1),
                   ("text/uri-list", gtk.TARGET_SAME_APP, 2),
                   ("text/uri-list", 0, 3)]
        self.drag_source_set(
            gtk.gdk.BUTTON1_MASK|gtk.gdk.CONTROL_MASK, targets,
            gtk.gdk.ACTION_DEFAULT|gtk.gdk.ACTION_COPY)
        self.drag_dest_set(
            gtk.DEST_DEFAULT_ALL, targets, gtk.gdk.ACTION_DEFAULT)
        self.enable_model_drag_dest(targets, gtk.gdk.ACTION_DEFAULT)
        self.connect('drag-begin', self.__drag_begin)
        self.connect('drag-data-get', self.__drag_data_get)
        self.connect('drag-data-received', self.__drag_data_received)

    def __drag_begin(self, view, ctx):
        model, paths = self.get_selection().get_selected_rows()
        if paths:
            icon = self.create_row_drag_icon(paths[-1])
            self.drag_source_set_icon(icon.get_colormap(), icon)
        else: return True

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        model, paths = self.get_selection().get_selected_rows()
        print "START DRAG DATA GET"
        print "got paths", paths
        print "target id is", tid
        uris = ["file:///" + model[path][0] for path in paths]
        print "uris are", uris
        sel.set_uris(uris)
        print "END DRAG DATA GET"

    def __drag_data_received(self, view, ctx, x, y, sel, info, etime):
        model = view.get_model()
        print "START DRAG DATA RECEIVED"
        names = [s[8:] for s in sel.get_uris()]
        print "names are", names
        try: path, position = self.get_dest_row_at_pos(x, y)
        except TypeError: path = len(model - 1)
        print "dropping at", path
        ctx.finish(True, True, etime)
        print "END DRAG DATA RECEIVED"

    def _make_model(self):
        m = gtk.ListStore(str)
        for i in range(10):
            m.append(row=["Item%d" % i])
        return m

if __name__ == "__main__":
    w = gtk.Window()
    w.add(gtk.HBox(spacing=3))
    w.child.pack_start(View("Number 1"))
    w.child.pack_start(View("Number 2"))
    w.show_all()
    gtk.main()

    
