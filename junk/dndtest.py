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
        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        self.drag_source_set(
            gtk.gdk.BUTTON1_MASK|gtk.gdk.CONTROL_MASK, targets,
            gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_MOVE)
        self.drag_dest_set(gtk.DEST_DEFAULT_ALL, targets,
                           gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_MOVE)
        self.connect('drag-begin', self.__drag_begin)
        self.connect('drag-data-delete', self.__drag_data_delete)
        #self.connect('drag-drop', self.__drag_drop)
        self.connect('drag-motion', self.__drag_motion)
        self.connect('drag-data-get', self.__drag_data_get)
        self.connect('drag-data-received', self.__drag_data_received)

    def __drag_begin(self, view, ctx):
        model, paths = self.get_selection().get_selected_rows()
        if paths:
            icon = self.create_row_drag_icon(paths[-1])
            self.drag_source_set_icon(icon.get_colormap(), icon)
        else: return True

    def __drag_data_delete(self, view, ctx):
        if ctx.is_source and ctx.action == gtk.gdk.ACTION_MOVE:
            # For some reason it wants to delete twice.
            print "I should delete."
            map(self.get_model().remove, self.__iters)
            self.__iters = []

    def __drag_motion(self, view, ctx, x, y, time):
        try: self.set_drag_dest_row(*self.get_dest_row_at_pos(x, y))
        except TypeError:
            self.set_drag_dest_row(len(self.get_model()) - 1,
                                   gtk.TREE_VIEW_DROP_AFTER)
        if ctx.get_source_widget() == self: kind = gtk.gdk.ACTION_MOVE
        else: kind = gtk.gdk.ACTION_COPY
        ctx.drag_status(kind, time)
        return True

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        model, paths = self.get_selection().get_selected_rows()
        print "START DRAG DATA GET"
        uris = ["file:///" + model[path][0] for path in paths]
        if tid == 1:
            print "Asked for internal URIs"
            if ctx.action == gtk.gdk.ACTION_MOVE:
                print "And delete them too!"
                self.__iters = map(model.get_iter, paths)
            else:
                self.__iters = []
            # We also add them to the library here.
            sel.set("text/x-quodlibet-songs", 8,
                    "\x00".join(uris))
        else:
            print "Asked for external URIs."
            sel.set_uris(uris)
        return True

    def __drag_data_received(self, view, ctx, x, y, sel, info, etime):
        model = view.get_model()
        print "START DRAG DATA RECEIVED"
        if info == 1:
            print "Getting filenames from QL"
            files = sel.data.split("\x00")
        elif info == 2:
            print "Getting URIs from elsewhere."
            files = sel.get_uris()
        try: path, position = self.get_dest_row_at_pos(x, y)
        except TypeError:
            path, position = len(model) - 1, gtk.TREE_VIEW_DROP_AFTER
        iter = model.get_iter(path)
        song = files.pop(0)
        if position in (gtk.TREE_VIEW_DROP_BEFORE,
                        gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
            iter = model.insert_before(iter, [song[8:]])
        else:
            iter = model.insert_after(iter, [song[8:]])
        for song in files:
            iter = model.insert_after(iter, [song[8:]])
        ctx.finish(True, True, etime)
        return True

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

    
